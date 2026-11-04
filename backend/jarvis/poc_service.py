"""A0 återanvänder JARVIS transaktioner, ägargräns och DEMO-databas."""
import json
from uuid import UUID

from . import config
from .budget import RuleError
from .db import connect, event, now, uid
from .poc_a0 import NOTICE, VERSION, build_snapshot, canonical, digest, suite
from .roles import ROLES


def require_demo():
    if config.mode() != "DEMO":
        raise RuleError("Researchlabb A0 får bara köras och läsas i DEMO. LIVE är inte anslutet till labbet.")


def _decode(row):
    try:
        payload = json.loads(row["payload"])
        valid = digest(payload) == row["digest"]
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise RuleError("A0-körningens kontrollsumma stämmer inte. Resultatet får inte användas.")
    return {"run": payload, "sha256": row["digest"]}


def _summary(row):
    run = _decode(row)["run"]
    return {k: run[k] for k in ("id", "created", "stage", "version", "suite_hash", "report_count", "simulated_steps", "external_calls", "cost_ore")}


def catalog():
    definition = suite()
    with connect() as c:
        state = c.execute("SELECT state FROM settings WHERE id=1").fetchone()[0]
        saved = c.execute("SELECT * FROM research_a0_runs ORDER BY created DESC, id DESC LIMIT 30").fetchall() if config.mode() == "DEMO" else []
    return {"version": VERSION, "stage": "A0", "notice": NOTICE, "suite_hash": digest(definition),
            "mode": config.mode(), "state": state,
            "topics": [{"id": e["package"]["id"], "title": e["package"]["title"], "question": e["package"]["question"]} for e in definition["examples"]],
            "runs": [_summary(row) for row in saved]}


def get_run(run_id):
    require_demo()
    with connect() as c:
        row = c.execute("SELECT * FROM research_a0_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    return _decode(row)


def start(action_id, suite_hash):
    require_demo()
    try:
        action_id = str(UUID(action_id))
    except (ValueError, AttributeError):
        raise RuleError("Ett giltigt åtgärds-ID krävs.") from None
    with connect(True) as c:
        existing = c.execute("SELECT * FROM research_a0_runs WHERE action_id=?", (action_id,)).fetchone()
        if existing:
            if existing["suite_hash"] != suite_hash:
                raise RuleError("Åtgärds-ID:t är redan bundet till ett annat underlag.")
            return _decode(existing)
        if c.execute("SELECT state FROM settings WHERE id=1").fetchone()[0] != "running":
            raise RuleError("A0 är pausat eller nödstoppat. Återuppta först.")
        if c.execute("SELECT COUNT(*) FROM research_a0_runs").fetchone()[0] >= 100:
            raise RuleError("A0-arkivet har nått gränsen på 100 körningar. Inget nytt arbete startades.")
        if suite_hash != digest(suite()):
            raise RuleError("Demounderlaget har ändrats. Läs in Researchlabb igen före start.")
        payload = build_snapshot(ROLES)
        payload.update(id=uid(), action_id=action_id, created=now())
        checksum = digest(payload)
        c.execute("INSERT INTO research_a0_runs VALUES(?,?,?,?,?,?)",
                  (payload["id"], action_id, suite_hash, payload["created"], canonical(payload), checksum))
        event(c, "research_a0", "A0-demonstration sparad: 9 syntetiska rapporter, 15 simulerade steg, 0 externa anrop.")
        return {"run": payload, "sha256": checksum}
