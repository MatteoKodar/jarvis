import asyncio
import json
import signal
import time
from . import config, demo
from .budget import RuleError
from .db import connect, initialize, uid, now, pack, event
from .service import add_task, create_proposal
from . import dispatch

LEASE = 120

def heartbeat(worker_id):
    with connect(True) as c:
        c.execute("INSERT INTO workers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET heartbeat=excluded.heartbeat", (worker_id, time.time()))

def claim():
    with connect(True) as c:
        stale = c.execute("SELECT id FROM tasks WHERE status='running' AND lease_until<?", (time.time(),)).fetchall()
        for row in stale:
            dispatch.recover(c, row[0])
            # Do not replay a request with an uncertain provider outcome.
            c.execute("UPDATE tasks SET status='blocked',error='Worker avbröts. Granska resultat och eventuell debitering; ingen automatisk omkörning.' WHERE id=?", (row[0],))
            c.execute("UPDATE reservations SET status='unknown' WHERE task_id=? AND status='held'", (row[0],))
            c.execute("UPDATE runs SET state='unknown',finished=? WHERE task_id=? AND state='running'", (now(), row[0]))
            event(c, "blocked", "Avbruten körning kräver manuell granskning", row[0])
        if c.execute("SELECT state FROM settings").fetchone()[0] != "running":
            return None
        if c.execute("SELECT COUNT(*) FROM tasks WHERE status='running'").fetchone()[0] >= 2:
            return None
        row = c.execute("SELECT * FROM tasks WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            return None
        c.execute("UPDATE tasks SET status='running',lease_until=?,attempts=attempts+1 WHERE id=?", (time.time()+LEASE, row["id"]))
        run_id = uid()
        epoch = c.execute("SELECT epoch FROM dispatch_control WHERE id=1").fetchone()[0]
        c.execute("INSERT INTO runs(id,task_id,started,state,dispatch_epoch) VALUES(?,?,?,'running',?)", (run_id, row["id"], now(), epoch))
        event(c, "started", "Arbete startat: " + row["title"][:150], row["id"])
        return dict(c.execute("SELECT * FROM tasks WHERE id=?", (row["id"],)).fetchone()) | {"run_id": run_id}

def finish(task, output):
    if output.candidates:
        raise RuleError("Affärsidékandidater är arkiverade. Endast fotbollsanalys stöds i det aktiva flödet.")
    result = output.model_dump()
    with connect(True) as c:
        # A late completion cannot overwrite a recovered or emergency-stopped task.
        current = c.execute("SELECT * FROM tasks WHERE id=?", (task["id"],)).fetchone()
        run = c.execute("SELECT * FROM runs WHERE id=? AND task_id=? AND state='running'", (task.get("run_id"), task["id"])).fetchone()
        if not current or current["status"] != "running" or not run:
            return
        task = dict(current)
        stopped = (c.execute("SELECT state FROM settings").fetchone()[0] == "stopped"
                   or run["dispatch_epoch"] != c.execute("SELECT epoch FROM dispatch_control").fetchone()[0])
        c.execute("UPDATE tasks SET result=?,status=?,lease_until=NULL WHERE id=?", (pack(result), "blocked" if stopped or output.blocked else "done", task["id"]))
        c.execute("UPDATE runs SET state='done',finished=? WHERE task_id=? AND state='running'", (now(), task["id"]))
        c.execute("INSERT INTO files VALUES(?,?,?,?,?)", (uid(), task["id"], f"{config.mode().lower()}-rapport-{task['id'][:8]}.txt", pack(result), now()))
        if task["phase"] == "plan" and not stopped and not output.blocked:
            create_proposal(c, task, result)
        elif task["phase"] == "work" and not stopped:
            c.execute("UPDATE tasks SET status='review' WHERE id=?", (task["id"],))
            context = json.loads(task["context"])
            add_task(c, action_id="review:"+task["id"], agent_id="critic", title="Granska: " + task["title"],
                     context=pack(result), criteria="Bedöm kvalitet och belägg. Blockera vid otillräckligt underlag.",
                     cap=context.get("review_cap", task["cap"]), phase="review", parent_id=task["id"], project_id=task["project_id"])
        elif task["phase"] == "review" and not stopped:
            c.execute("UPDATE tasks SET status=? WHERE id=?", ("blocked" if output.blocked else "done", task["parent_id"]))
        event(c, "result", "Resultat sparat" + ("; fortsatt arbete blockerat" if stopped or output.blocked else ""), task["id"])

def fail(task, reason):
    with connect(True) as c:
        dispatch.recover(c, task["id"])
        c.execute("UPDATE tasks SET status='blocked',error=?,lease_until=NULL WHERE id=? AND status='running'", (reason, task["id"]))
        c.execute("UPDATE runs SET state='blocked',finished=? WHERE task_id=? AND state='running'", (now(), task["id"]))
        event(c, "blocked", reason, task["id"])

async def execute(task):
    try:
        if config.mode() == "DEMO":
            await asyncio.sleep(0.15)
            output = demo.run(task)
        else:
            from .live import run
            output = await run(task)
        finish(task, output)
    except asyncio.CancelledError:
        fail(task, "Avbrutet. Redan skickade anrop kan vara debiterade; se reservationer.")
        raise
    except RuleError as exc:
        fail(task, str(exc))
    except Exception:
        # Never store provider error bodies, prompts, keys or credentials in logs.
        fail(task, "Körningen misslyckades. Kontrollera konfiguration och okända reservationer. Ingen automatisk omkörning.")

async def main():
    initialize()
    worker_id = uid()
    active = set()
    try:
        while True:
            heartbeat(worker_id)
            from .schedule import tick
            tick()
            with connect() as c:
                stopped = c.execute("SELECT state FROM settings").fetchone()[0] == "stopped"
            if stopped:
                for job in active:
                    job.cancel()
            active = {job for job in active if not job.done()}
            while len(active) < 2:
                task = claim()
                if task is None:
                    break
                active.add(asyncio.create_task(execute(task)))
            await asyncio.sleep(1)
    finally:
        for job in active:
            job.cancel()
        await asyncio.gather(*active, return_exceptions=True)
        with connect(True) as c:
            c.execute("DELETE FROM workers WHERE id=?", (worker_id,))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
