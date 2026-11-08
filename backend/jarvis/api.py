import asyncio
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, ValidationError
from . import config, auth, service, poc_service, odds_service
from .budget import RuleError, totals
from .db import initialize, connect, rows, now, uid, day, pack, event
from .models import Strict
from .odds_lab import Start as OddsStart, ImportSnapshot as OddsSnapshot, Result as OddsResult, Cost as OddsCost
from .odds_lab import Action as DemoAction
from . import betting_demo_service
from .betting_demo_service import Decision as DemoDecision, ApprovedBatch as DemoBatch
from .paper_data import PaperInput
from .paper_review import build_review as build_paper_review, ContractDrift
from .paper_evaluation import evaluate as evaluate_paper, ReportMismatch

@asynccontextmanager
async def lifespan(app):
    initialize()
    origin = os.getenv("JARVIS_ORIGIN", "http://127.0.0.1:8000")
    if not origin.startswith(("http://127.0.0.1:", "http://localhost:")):
        if not origin.startswith("https://") or os.getenv("JARVIS_SECURE_COOKIE") != "true":
            raise RuntimeError("Publik drift kräver HTTPS och Secure-cookie.")
    yield

app = FastAPI(title="JARVIS", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

@app.middleware("http")
async def security_headers(request, call_next):
    if int(request.headers.get("content-length", "0")) > 50000:
        return JSONResponse({"detail": "För stor begäran"}, status_code=413)
    if request.method == "POST" and request.url.path.startswith(("/api/odds-lab/", "/api/betting-demo/")):
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 50000:
                return JSONResponse({"detail": "För stor begäran"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.exception_handler(RuleError)
async def rule_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)

class Login(Strict):
    password: str = Field(min_length=1, max_length=256)

@app.get("/api/setup")
def setup_status(request: Request):
    with connect() as c:
        needed = c.execute("SELECT 1 FROM owner WHERE id=1").fetchone() is None
    return {"needed": needed, "allowed": needed and auth.local_setup_allowed(request)}

class FirstOwner(Strict):
    password: str = Field(min_length=12, max_length=256)

@app.post("/api/setup")
def setup_owner(body: FirstOwner, request: Request, response: Response):
    auth.create_first_owner(request, body.password)
    return login(Login(password=body.password), request, response)

@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    token, csrf = auth.login(request, body.password)
    response.set_cookie("jarvis_session", token, httponly=True, samesite="strict", secure=os.getenv("JARVIS_SECURE_COOKIE") == "true", max_age=43200)
    return {"csrf": csrf}

@app.get("/api/session")
def session(owner=Depends(auth.authenticate)):
    return {"csrf": owner["csrf"]}

@app.post("/api/logout")
def logout(request: Request, response: Response, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (owner["token_hash"],))
    response.delete_cookie("jarvis_session")
    return {"ok": True}

@app.get("/api/state")
def state(owner=Depends(auth.authenticate)):
    return service.snapshot()


class PaperReviewRequest(Strict):
    input: dict


class PaperEvaluateRequest(PaperReviewRequest):
    results: dict
    expected_report_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


def _paper_request(body, evaluate=False):
    betting_demo_service.require_demo()
    with connect() as c:
        if c.execute('SELECT state FROM settings WHERE id=1').fetchone()[0] != 'running':
            raise RuleError('Pappersgranskningen kräver att demot uttryckligen återupptas.')
    try:
        data = PaperInput.model_validate(body.input)
        return evaluate_paper(data, body.results, body.expected_report_hash) if evaluate else build_paper_review(data)
    except (ContractDrift, ReportMismatch) as exc:
        raise HTTPException(409, str(exc)) from None
    except ValidationError as exc:
        error = exc.errors(include_url=False, include_context=False)[0]
        raise HTTPException(422, 'Ogiltig fil vid '+'.'.join(str(v) for v in error['loc'])+': '+error['msg']) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post('/api/betting-demo/paper-replay/review')
def paper_review(body: PaperReviewRequest, owner=Depends(auth.authenticate)):
    return _paper_request(body)


@app.post('/api/betting-demo/paper-replay/evaluate')
def paper_evaluate(body: PaperEvaluateRequest, owner=Depends(auth.authenticate)):
    return _paper_request(body, evaluate=True)

class Control(Strict):
    state: Literal["running", "paused", "stopped"]

@app.post("/api/control")
def control(body: Control, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        current = c.execute("SELECT state FROM settings").fetchone()[0]
        if current == "stopped" and body.state == "paused":
            raise RuleError("Nödstopp kan bara hävas med Återuppta.")
        from .dispatch import control as dispatch_control
        dispatch_control(c, body.state)
        event(c, "control", {"running": "Ägaren återupptog arbetet", "paused": "Paus: inga nya uppgifter startar", "stopped": "Nödstopp: inga nya anrop. Pågående anrop försöker avbrytas; redan skickat arbete kan debiteras."}[body.state])
    return {"ok": True}

class Round(Strict):
    goal: str = Field(min_length=5, max_length=2000)
    cap: int = Field(ge=0, le=50000)
    action_id: str = Field(min_length=8, max_length=100)

@app.post("/api/rounds")
def new_round(body: Round, owner=Depends(auth.authenticate)):
    return {"task_id": service.start_round(body.goal, body.cap, body.action_id)}

class Decision(Strict):
    version: int
    digest: str
    decision: Literal["approved", "rejected", "changes"]
    note: str = Field(default="", max_length=2000)

@app.post("/api/proposals/{pid}/decision")
def decision(pid: str, body: Decision, owner=Depends(auth.authenticate)):
    service.decide(pid, **body.model_dump())
    return {"ok": True}

class Revision(Strict):
    title: str = Field(min_length=5, max_length=2000)
    cap: int = Field(ge=0, le=50000)

@app.post("/api/proposals/{pid}/revise")
def revision(pid: str, body: Revision, owner=Depends(auth.authenticate)):
    return {"id": service.revise(pid, body.title, body.cap)}

class Chat(Strict):
    message: str = Field(min_length=1, max_length=2000)

@app.post("/api/chat")
def chat(body: Chat, owner=Depends(auth.authenticate)):
    s = service.snapshot()
    pending = len([p for p in s["proposals"] if p["status"] == "pending"])
    text = body.message.lower()
    if any(word in text for word in ["kost", "budget", "använt", "mycket"]):
        b = s["settings"]
        answer = f"Registrerat: {b['spent']/100:.2f} SEK. Reserverat: {b['reserved']/100:.2f} SEK. Tillgängligt: {b['available']/100:.2f} SEK. Se Ekonomi för uppskattningar och manuella poster."
    elif any(word in text for word in ["idé", "kandidat", "valde", "varför"]):
        answer = "Projektets enda fokus är nu fotbollsodds och simulerad uppföljning. Allmän affärsidéresearch är arkiverad. Se Oddslabb för sparade exempel och observationer; chatten gör inga egna odds- eller vinstbedömningar."
    elif any(word in text for word in ["status", "jobbar", "läget", "gör ni"]):
        answer = f"Databasstatus: {sum(t['status']=='running' for t in s['tasks'])} uppgifter pågår, {pending} beslut väntar. Huvudmål: {s['settings']['goal']}"
    else:
        answer = "Jag har sparat din instruktion. För att börja arbeta: använd Starta arbetsomgång och ange instruktionen som mål. VD skapar först ett förslag att granska. Chatten kan inte godkänna handlingar."
    with connect(True) as c:
        for role, message in [("user", body.message), ("assistant", answer)]:
            c.execute("INSERT INTO messages(role,content,created) VALUES(?,?,?)", (role, message, now()))
        event(c, "chat", "Statuschatt uppdaterad utan AI-anrop")
    return {"answer": answer}

class Settings(Strict):
    total: int = Field(ge=0, le=100000000)
    locked: int = Field(ge=0, le=100000000)
    daily: int = Field(ge=0, le=1000000)
    per_task: int = Field(ge=0, le=50000)

@app.post("/api/settings")
def settings(body: Settings, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        b = totals(c)
        if body.total - body.locked < b["spent"] + b["reserved"] or body.per_task > body.daily:
            raise RuleError("Gränserna täcker inte bokförd användning/reservationer eller uppgiftstaket överstiger dagstaket.")
        c.execute("UPDATE settings SET total=?,locked=?,daily=?,per_task=? WHERE id=1", (body.total, body.locked, body.daily, body.per_task))
        event(c, "settings", "Ägaren ändrade budgetgränserna")
    return {"ok": True}

class Schedule(Strict):
    enabled: bool
    at: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    goal: str = Field(min_length=5, max_length=2000)
    cap: int = Field(ge=0, le=50000)
    remaining: int = Field(ge=1, le=7)

@app.post("/api/schedule")
def schedule(body: Schedule, owner=Depends(auth.authenticate)):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    with connect(True) as c:
        if body.cap > totals(c)["per_task"]:
            raise RuleError("Schemat överskrider uppgiftstaket.")
        expires = (datetime.now(ZoneInfo('Europe/Stockholm')).date()+timedelta(days=6)).isoformat()
        c.execute("UPDATE schedule SET enabled=?,at=?,goal=?,cap=?,remaining=?,version=version+1,last_day='',expires=? WHERE id=1", (body.enabled, body.at, body.goal, body.cap, body.remaining, expires))
        event(c, "schedule", "Ägaren godkände ett begränsat VD-schema" if body.enabled else "Ägaren stängde av schemat")
    return {"ok": True}

class ManualCost(Strict):
    amount: int = Field(ge=1, le=10000000)
    note: str = Field(min_length=3, max_length=1000)
    action_id: str = Field(min_length=8, max_length=100)

@app.post("/api/costs")
def manual_cost(body: ManualCost, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        existing = c.execute("SELECT * FROM costs WHERE id=?", (body.action_id,)).fetchone()
        if existing:
            try:
                metadata = json.loads(existing["metadata"])
            except (ValueError, TypeError):
                metadata = None
            if (existing["kind"] != "manual" or existing["task_id"] is not None
                    or existing["agent_id"] is not None or existing["amount"] != body.amount
                    or not isinstance(metadata, dict) or metadata.get("note") != body.note):
                raise RuleError("Åtgärds-ID:t är bundet till annat innehåll. Kontrollera den sparade kostnaden innan du skapar en ny begäran.")
            return {"ok": True}
        if body.amount > totals(c)["available"]:
            raise RuleError("Kostnaden ryms inte i användbar budget. Justera budgeten först.")
        c.execute("INSERT INTO costs VALUES(?,NULL,NULL,?,?,'manual',?,?)", (body.action_id, body.amount, day(), pack({"note": body.note, "verified": False}), now()))
        event(c, "cost", "Manuell kostnad registrerad, ej verifierad mot leverantör")
    return {"ok": True}

class Reconcile(Strict):
    amount: int = Field(ge=0, le=10000000)
    note: str = Field(min_length=10, max_length=2000)

@app.post("/api/reservations/{rid}/reconcile")
def reconcile(rid: str, body: Reconcile, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        r = c.execute("SELECT * FROM reservations WHERE id=? AND status='unknown'", (rid,)).fetchone()
        if not r:
            raise RuleError("Ingen okänd reservation att stämma av.")
        agent = c.execute("SELECT agent_id FROM tasks WHERE id=?", (r["task_id"],)).fetchone()[0]
        c.execute("UPDATE reservations SET status='reconciled' WHERE id=?", (rid,))
        c.execute("INSERT INTO costs VALUES(?,?,?,?,?,'owner_reconciled',?,?)", (uid(), r["task_id"], agent, body.amount, r["day"], pack({"note": body.note, "original": json.loads(r["metadata"])}), now()))
        event(c, "reconciled", "Ägaren stämde av okänd debitering: " + body.note, r["task_id"])
    return {"ok": True}

@app.post("/api/projects/{pid}/close")
def close_project(pid: str, owner=Depends(auth.authenticate)):
    with connect(True) as c:
        if c.execute("SELECT 1 FROM tasks WHERE project_id=? AND status IN ('queued','running','review')", (pid,)).fetchone():
            raise RuleError("Projektet har ofärdiga uppgifter.")
        c.execute("UPDATE projects SET state='closed' WHERE id=?", (pid,))
        event(c, "project", "Ägaren avslutade projektet")
    return {"ok": True}

@app.get("/api/files/{fid}")
def download(fid: str, owner=Depends(auth.authenticate)):
    with connect() as c:
        f = c.execute("SELECT * FROM files WHERE id=?", (fid,)).fetchone()
    if not f:
        raise HTTPException(404, "Filen saknas")
    # Database IDs only: no filesystem path is accepted. Always download as plain text.
    return Response(f["content"], media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{f["name"]}"'})

@app.get("/api/events")
async def events(request: Request, owner=Depends(auth.authenticate)):
    try:
        cursor = int(request.headers.get("last-event-id", "0"))
    except ValueError:
        cursor = 0
    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            with connect() as c:
                if not c.execute("SELECT 1 FROM sessions WHERE token_hash=? AND expires>?", (owner["token_hash"], time.time())).fetchone():
                    return
                updates = rows(c, "SELECT * FROM events WHERE id>? ORDER BY id LIMIT 100", (cursor,))
            for item in updates:
                cursor = item["id"]
                yield f"id: {cursor}\nevent: update\ndata: {pack(item)}\n\n"
            yield ": heartbeat\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

class A0Start(Strict):
    action_id: str = Field(min_length=36, max_length=36)
    suite_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

@app.get("/api/research-poc/a0")
def a0_catalog(owner=Depends(auth.authenticate)):
    return poc_service.catalog()

@app.post("/api/research-poc/a0/runs")
def a0_start(body: A0Start, owner=Depends(auth.authenticate)):
    raise RuleError("Researchlabb A0 är arkiverat efter fokusbytet. Sparade resultat kan läsas; nya A0-körningar startas inte.")

@app.get("/api/research-poc/a0/runs/{run_id}")
def a0_run(run_id: str, owner=Depends(auth.authenticate)):
    result = poc_service.get_run(run_id)
    if result is None:
        raise HTTPException(404, "A0-körningen saknas.")
    return result

@app.get("/api/research-poc/a0/runs/{run_id}/export")
def a0_export(run_id: str, owner=Depends(auth.authenticate)):
    result = poc_service.get_run(run_id)
    if result is None:
        raise HTTPException(404, "A0-körningen saknas.")
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="jarvis-a0-{result["run"]["id"]}.json"'})

@app.get("/api/odds-lab")
def odds_catalog(owner=Depends(auth.authenticate)):
    return odds_service.catalog()

@app.get("/api/odds-lab/template")
def odds_template(owner=Depends(auth.authenticate)):
    return odds_service.template()

@app.post("/api/odds-lab/runs")
def odds_start(body: OddsStart, owner=Depends(auth.authenticate)):
    return odds_service.start(body)

@app.get("/api/odds-lab/runs/{run_id}")
def odds_run(run_id: str, owner=Depends(auth.authenticate)):
    return odds_service.get_run(run_id)

@app.get("/api/odds-lab/runs/{run_id}/export")
def odds_export(run_id: str, owner=Depends(auth.authenticate)):
    result = odds_service.get_run(run_id)
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="jarvis-odds-{result["run"]["id"]}.json"'})

@app.post("/api/odds-lab/runs/{run_id}/snapshots")
def odds_snapshot(run_id: str, body: OddsSnapshot, owner=Depends(auth.authenticate)):
    return odds_service.import_snapshot(run_id, body)

@app.post("/api/odds-lab/runs/{run_id}/results")
def odds_result(run_id: str, body: OddsResult, owner=Depends(auth.authenticate)):
    return odds_service.record_result(run_id, body)

@app.post("/api/odds-lab/runs/{run_id}/costs")
def odds_cost(run_id: str, body: OddsCost, owner=Depends(auth.authenticate)):
    return odds_service.record_cost(run_id, body)

@app.get("/api/betting-demo/sessions")
def demo_sessions(owner=Depends(auth.authenticate)):
    return betting_demo_service.catalog()

@app.post("/api/betting-demo/sessions")
def demo_create(body: DemoAction, owner=Depends(auth.authenticate)):
    return betting_demo_service.create(body)

@app.get("/api/betting-demo/sessions/{session_id}")
def demo_session(session_id: str, owner=Depends(auth.authenticate)):
    return betting_demo_service.get_session(session_id)

@app.post("/api/betting-demo/sessions/{session_id}/analyze")
def demo_analyze(session_id: str, body: DemoAction, owner=Depends(auth.authenticate)):
    return betting_demo_service.analyze(session_id, body)

@app.post("/api/betting-demo/sessions/{session_id}/decision")
def demo_decision(session_id: str, body: DemoDecision, owner=Depends(auth.authenticate)):
    return betting_demo_service.decide(session_id, body)

@app.post("/api/betting-demo/sessions/{session_id}/simulate")
def demo_simulate(session_id: str, body: DemoBatch, owner=Depends(auth.authenticate)):
    return betting_demo_service.simulate(session_id, body)

@app.post("/api/betting-demo/sessions/{session_id}/settle")
def demo_settle(session_id: str, body: DemoAction, owner=Depends(auth.authenticate)):
    return betting_demo_service.settle(session_id, body)

@app.get("/api/documents")
def document_catalog(owner=Depends(auth.authenticate)):
    from .documents import catalog
    return catalog()

@app.get("/api/documents/{version}/{document_id}")
def document_read(version: str, document_id: str, owner=Depends(auth.authenticate)):
    from .documents import read
    document = read(version, document_id)
    if document is None:
        raise HTTPException(404, "Dokumentet finns inte bland de publicerade dokumenten.")
    return document

dist = config.ROOT / "frontend/dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

