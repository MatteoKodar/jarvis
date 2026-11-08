import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from . import config
from .budget import RuleError, totals
from .db import connect, uid, now, pack, event, rows
from .roles import ROLES
from .focus import VERSION as FOCUS_VERSION, MISSION, SCOPE

def add_task(c, *, action_id, agent_id, title, context, criteria, cap, phase, parent_id=None, project_id=None):
    existing = c.execute("SELECT id FROM tasks WHERE action_id=?", (action_id,)).fetchone()
    if existing:
        return existing[0]
    if agent_id not in ROLES or phase not in {"plan", "work", "review"}:
        raise RuleError("Otillåten roll eller arbetsfas.")
    if not title.strip() or not criteria.strip() or cap < 0:
        raise RuleError("Mål, färdigkriterier och kostnadstak krävs.")
    if len(title) > 2000 or len(context) > 18000:
        raise RuleError("Uppgiftens underlag överskrider storleksgränsen; inget underlag kapas.")
    settings = totals(c)
    if cap > settings["per_task"]:
        raise RuleError("Kostnadstaket överskrider gränsen per uppgift.")
    tid = uid()
    c.execute("INSERT INTO tasks(id,action_id,project_id,agent_id,title,context,criteria,cap,phase,status,parent_id,created) VALUES(?,?,?,?,?,?,?,?,?,'queued',?,?)",
              (tid, action_id, project_id, agent_id, title, context, criteria, cap, phase, parent_id, now()))
    event(c, "task", "Uppgift planerad: " + title[:200], tid)
    return tid

def start_round(goal, cap, action_id):
    with connect(True) as c:
        old = c.execute("SELECT * FROM tasks WHERE action_id=?", (action_id,)).fetchone()
        if old:
            if (old["agent_id"] != "ceo" or old["phase"] != "plan"
                    or old["title"] != goal or old["cap"] != cap):
                raise RuleError("Åtgärds-ID:t är bundet till annat innehåll. Kontrollera den sparade arbetsomgången innan du skapar en ny begäran.")
            return old["id"]
        if config.mode() == "LIVE" and config.missing_live():
            raise RuleError("LIVE saknar: " + ", ".join(config.missing_live()))
        if c.execute("SELECT state FROM settings").fetchone()[0] != "running":
            raise RuleError("Arbetet är pausat eller nödstoppat. Återuppta först.")
        if c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued','running','approval','review')").fetchone()[0] >= 12:
            raise RuleError("Kön är full (12 öppna uppgifter). Slutför befintligt arbete först.")
        c.execute("UPDATE settings SET goal=? WHERE id=1", (goal,))
        return add_task(c, action_id=action_id, agent_id="ceo", title=goal, context=f"Projektfokus: {MISSION} {SCOPE} Ägarens uppdrag är en avgränsning inom detta. Skapa bara ett granskningsbart internt analysförslag.",
                        criteria="Ett konkret förslag med risker, alternativ och färdigkriterier.", cap=cap, phase="plan")

def create_proposal(c, task, result):
    agent = result["proposed_agent"]
    if agent not in ROLES or agent == "ceo":
        raise RuleError("VD föreslog en otillåten roll.")
    payload = {"action": "internal_work", "agent_id": agent, "title": result["next_action"],
               "target": task["title"], "content": result["summary"], "purpose": result["rationale"],
               "criteria": "Sparad rapport som skiljer belägg från antaganden, samt separat kritikergranskning.",
               "cap": task["cap"], "review_cap": task["cap"], "risks": result["risks"], "alternatives": result["alternatives"],
               "effect": "Köar en intern specialistuppgift och därefter högst en kritikergranskning. Inga köp, utskick eller publicering. Totalt tak är summan av båda uppgifternas tak."}
    pid = uid()
    digest = hashlib.sha256(pack(payload).encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    c.execute("INSERT INTO proposals(id,task_id,version,payload,digest,status,expires) VALUES(?,?,1,?,?,'pending',?)", (pid, task["id"], pack(payload), digest, expires))
    c.execute("UPDATE tasks SET status='approval' WHERE id=?", (task["id"],))
    event(c, "proposal", "Nytt förslag väntar på ägarbeslut", task["id"])

def decide(pid, version, digest, decision, note, actor="owner"):
    if actor != "owner":
        raise RuleError("Endast den autentiserade ägaren får besluta.")
    with connect(True) as c:
        p = c.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
        if not p or p["version"] != version or p["digest"] != digest:
            raise RuleError("Förslaget har ändrats. Läs den aktuella versionen före beslut.")
        previous = c.execute("SELECT decision FROM approvals WHERE proposal_id=? AND version=?", (pid, version)).fetchone()
        if previous:
            if previous[0] == decision:
                return
            raise RuleError("Denna version har redan ett annat beslut.")
        if p["status"] != "pending" or p["expires"] < now():
            raise RuleError("Förslaget är inte öppet eller har löpt ut.")
        if decision not in {"approved", "rejected", "changes"}:
            raise RuleError("Ogiltigt beslut.")
        payload = json.loads(p["payload"])
        if hashlib.sha256(pack(payload).encode()).hexdigest() != p["digest"]:
            raise RuleError("Förslagets innehåll matchar inte godkännandets kontrollsumma.")
        if decision == "approved":
            if payload["action"] != "internal_work":
                raise RuleError("Extern handling stöds inte.")
            project_id = None
            if payload["agent_id"] in {"developer", "designer"}:
                existing = c.execute("SELECT id FROM projects WHERE kind='development' AND state='active'").fetchone()
                if existing:
                    raise RuleError("Avsluta det aktiva utvecklingsprojektet först.")
                project_id = uid()
                c.execute("INSERT INTO projects VALUES(?,?,'active','development')", (project_id, payload["target"][:200]))
            add_task(c, action_id=f"approval:{pid}:{version}", agent_id=payload["agent_id"], title=payload["title"],
                     context=pack({"goal": payload["target"], "approved_content": payload["content"], "review_cap": payload["review_cap"]}),
                     criteria=payload["criteria"], cap=payload["cap"], phase="work", parent_id=p["task_id"], project_id=project_id)
        c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,'owner',?)", (uid(), pid, version, digest, decision, now()))
        c.execute("UPDATE proposals SET status=?,note=? WHERE id=?", (decision, note, pid))
        c.execute("UPDATE tasks SET status=? WHERE id=?", ("done" if decision == "approved" else "blocked", p["task_id"]))
        event(c, "decision", {"approved": "Godkänt och köat", "rejected": "Avslaget", "changes": "Ändring begärd"}[decision] + (": " + note if note else ""), p["task_id"])

def revise(pid, title, cap):
    with connect(True) as c:
        p = c.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
        if not p or p["status"] != "changes":
            raise RuleError("Begär ändring först. Ett godkänt förslag kan inte redigeras.")
        if cap > totals(c)["per_task"]:
            raise RuleError("För högt kostnadstak.")
        payload = json.loads(p["payload"])
        payload.update(title=title, cap=cap, review_cap=cap)
        digest = hashlib.sha256(pack(payload).encode()).hexdigest()
        c.execute("UPDATE proposals SET status='superseded' WHERE id=?", (pid,))
        new_id = uid()
        c.execute("INSERT INTO proposals(id,task_id,version,payload,digest,status,expires,note) VALUES(?,?,?,?,?,'pending',?,?)", (new_id, p["task_id"], p["version"]+1, pack(payload), digest, (datetime.now(timezone.utc)+timedelta(days=7)).isoformat(), p["note"]))
        c.execute("UPDATE tasks SET status='approval' WHERE id=?", (p["task_id"],))
        event(c, "proposal", "Ny förslagsversion kräver nytt ägarbeslut", p["task_id"])
        return new_id

def snapshot():
    with connect() as c:
        tasks = rows(c, "SELECT * FROM tasks ORDER BY created DESC")
        agents = []
        s = totals(c)
        for role in ROLES.values():
            history = [t for t in tasks if t["agent_id"] == role["id"]]
            active = next((t for t in history if t["status"] == "running"), None)
            pending = next((t for t in history if t["status"] == "queued"), None)
            latest = next((t for t in history if t["result"]), None)
            agents.append({**role, "status": "Arbetar" if active else "Pausad" if s["state"] != "running" else "Planerad" if pending else "Väntar", "task": active or pending,
                           "latest": json.loads(latest["result"])["summary"] if latest else None,
                           "usage": c.execute("SELECT COALESCE(SUM(amount),0) FROM costs WHERE agent_id=?", (role["id"],)).fetchone()[0]})
        proposals = rows(c, "SELECT * FROM proposals ORDER BY rowid DESC")
        for p in proposals:
            p["payload"] = json.loads(p["payload"])
        heartbeat = c.execute("SELECT MAX(heartbeat) FROM workers").fetchone()[0]
        return {"mode": config.mode(), "settings": s, "schedule": dict(c.execute("SELECT * FROM schedule WHERE id=1").fetchone()), "agents": agents, "tasks": tasks, "proposals": proposals,
                "projects": rows(c, "SELECT * FROM projects"), "ideas": [{**r, "data": json.loads(r["data"])} for r in rows(c, "SELECT * FROM ideas")],
                "sources": rows(c, "SELECT * FROM sources"), "costs": rows(c, "SELECT * FROM costs ORDER BY created DESC"),
                "reservations": rows(c, "SELECT * FROM reservations WHERE status IN ('held','unknown')"),
                "files": rows(c, "SELECT id,task_id,name,created FROM files ORDER BY created DESC"),
                "events": rows(c, "SELECT * FROM events ORDER BY id DESC LIMIT 300"), "messages": rows(c, "SELECT * FROM messages ORDER BY id"),
                "approvals": rows(c, "SELECT * FROM approvals ORDER BY created DESC"), "runs": rows(c, "SELECT * FROM runs ORDER BY started DESC"),
                "worker": {"heartbeat": heartbeat, "online": bool(heartbeat and time.time()-heartbeat < 15)},
                "live_missing": config.missing_live(), "focus": {"version": FOCUS_VERSION, "mission": MISSION, "scope": SCOPE},
                "integrations": {"payments": False, "publication": False, "outreach": False, "research": False, "odds_feed": False, "real_bets": False}}
