"""Fokusbyte prövas mot produktionsroller, utan den äldre testprofilens wiki-rättighet."""
import asyncio
import json
import time

import pytest

from jarvis import demo, dispatch, external_http, research, service, worker
from jarvis.budget import RuleError
from jarvis.db import connect, day, initialize, now, pack, uid
from jarvis.focus import MISSION, VERSION
from jarvis.models import AgentResult, Candidate
from jarvis.roles import ROLES


def test_exact_ten_football_roles_have_no_external_research_or_money_tools(client):
    assert set(ROLES) == {"ceo", "researcher", "analyst", "strategist", "developer", "designer", "marketer", "sales", "finance", "critic"}
    for role in ROLES.values():
        assert role["version"] == "2.0.0-football"
        assert MISSION in role["instructions"]
        assert set(role["tools"]) <= {"database_status"}
        assert "wikipedia_search" not in role["tools"]
        assert "Fältet candidates ska vara tomt" in role["instructions"]
        assert "placerat spel" in role["instructions"]
    snapshot = client.get("/api/state").json()
    assert snapshot["focus"]["mission"] == MISSION
    assert snapshot["focus"]["version"] == VERSION
    assert snapshot["settings"]["goal"] == MISSION


def test_demo_football_outputs_no_business_candidates_or_claimed_real_bets():
    for phase in ("plan", "work", "review"):
        result = demo.run({"phase": phase})
        assert result.candidates == []
        assert "DEMO" in result.summary
    assert demo.run({"phase": "review"}).blocked is True


def test_new_round_binds_football_context_and_chat_does_not_start_legacy_research(client):
    assert client.post("/api/control", json={"state": "running"}).status_code == 200
    task_id = service.start_round("Granska senaste fotbollstestets datakvalitet", 500, uid())
    with connect() as c:
        task = dict(c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    assert MISSION in task["context"]
    assert "Projektfokus" in task["context"]
    before = len(service.snapshot()["tasks"])
    response = client.post("/api/chat", json={"message": "Vilka affärsidéer ska agenterna leta efter?"})
    assert response.status_code == 200
    assert "fotboll" in response.json()["answer"].lower()
    assert "arkiverad" in response.json()["answer"].lower()
    assert len(service.snapshot()["tasks"]) == before


def test_real_roles_deny_archived_wikipedia_before_transport_or_reservation(monkeypatch):
    for key, value in {"JARVIS_MODE": "LIVE", "OPENAI_API_KEY": "test-only-not-sent", "JARVIS_MODEL": "test-model",
                       "JARVIS_PRICED_MODEL": "test-model", "JARVIS_PRICE_VERSION": "test-v1", "JARVIS_INPUT_USD": "0.1",
                       "JARVIS_OUTPUT_USD": "0.4", "JARVIS_USD_SEK": "10", "JARVIS_PAID_ENABLED": "true",
                       "JARVIS_RESEARCH_ENABLED": "true", "JARVIS_AGENT_MODELS": "{}"}.items():
        monkeypatch.setenv(key, value)
    initialize()
    with connect(True) as c:
        c.execute("UPDATE settings SET state='running'")
        service.add_task(c, action_id=uid(), agent_id="researcher", title="Granska fotbollsdata", context="",
                         criteria="Dokumenterad datakontroll", cap=500, phase="work")
    handle = worker.claim()
    assert "wikipedia_search" not in ROLES["researcher"]["tools"]
    def forbidden():
        pytest.fail("Den arkiverade integrationsvägen får aldrig nå en transport.")
    monkeypatch.setattr(external_http, "model_transport", forbidden)
    monkeypatch.setattr(external_http, "research_transport", forbidden)
    with pytest.raises(RuleError, match="researchverktyget"):
        dispatch.prepare(handle, dispatch.WIKI)
    with pytest.raises(RuleError, match="researchverktyget"):
        asyncio.run(research.search(handle))
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM reservations").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0


def test_business_candidates_are_rejected_before_persistence(client):
    client.post("/api/control", json={"state": "running"})
    service.start_round("Granska fotbollsdata", 500, uid())
    task = worker.claim()
    candidate = Candidate(title="Äldre affärsidé", problem="p", audience="a", solution="s", competitors="c", distribution="d",
                          payment_signals="p", costs="c", risks="r", questions="q", willingness=0, reach=0,
                          test_cost=0, automation=0, advantage=0, evidence="Saknas")
    with pytest.raises(RuleError, match="arkiverade"):
        worker.finish(task, AgentResult(summary="Äldre svar", rationale="Test", candidates=[candidate]))
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM ideas").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0


@pytest.mark.parametrize("initial_state", ["running", "paused", "stopped"])
def test_migration_006_retires_legacy_work_preserves_money_history_and_stop(initial_state):
    with connect(True) as c:
        tasks = {}
        for status in ("queued", "running", "approval", "review", "done"):
            task_id = service.add_task(c, action_id="legacy-" + status, agent_id="researcher", title="Äldre affärsidéresearch",
                                       context="Äldre underlag", criteria="Äldre kriterier", cap=500, phase="work")
            c.execute("UPDATE tasks SET status=?,result=?,lease_until=? WHERE id=?",
                      (status, "sparat resultat" if status == "done" else None, time.time() + 600, task_id))
            tasks[status] = task_id
        run_ids = {}
        epoch = c.execute("SELECT epoch FROM dispatch_control").fetchone()[0]
        for status in ("running", "approval"):
            run_ids[status] = uid()
            c.execute("INSERT INTO runs(id,task_id,started,state,dispatch_epoch) VALUES(?,?,?,'running',?)",
                      (run_ids[status], tasks[status], now(), epoch))
        reservations = {}
        for name, task_status, amount, state in (("prepared", "running", 40, "held"), ("possible_send", "approval", 60, "held"),
                                                  ("orphan", "review", 80, "held"), ("prior_unknown", "done", 100, "unknown")):
            reservation_id = uid()
            reservations[name] = reservation_id
            c.execute("INSERT INTO reservations VALUES(?,?,?,?,?,?)", (reservation_id, tasks[task_status], amount, day(), state, pack({"source": name})))
            if name in {"prepared", "possible_send"}:
                c.execute("INSERT INTO operations(id,task_id,run_id,kind,slot,version,epoch,input_hash,frozen,reservation_id,state,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                          (uid(), tasks[task_status], run_ids[task_status], "model.responses", "model.responses:1", "dispatch-v1", epoch,
                           "f" * 64, "{}", reservation_id, name, now()))
        c.execute("INSERT INTO costs VALUES(?,?,?,?,?,?,?,?)", (uid(), tasks["done"], "researcher", 37, day(), "estimate", "{}", now()))
        c.execute("INSERT INTO ideas VALUES(?,?,?,?)",
                  (uid(), tasks["done"], pack({"legacy": True}), "archived"))
        c.execute("INSERT INTO files VALUES(?,?,?,?,?)", (uid(), tasks["done"], "old-report.txt", "Bevarat underlag", now()))
        c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)", (uid(), tasks["done"], "https://example.invalid/legacy", "Äldre källa", now(), "legacy", "Äldre observation", "FAKTA"))
        # Two prior proposals: pending is retired; approved remains an audit record.
        pending, approved = uid(), uid()
        for pid, task_status, state in ((pending, "approval", "pending"), (approved, "done", "approved")):
            c.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?)",
                      (pid, tasks[task_status], 1, "{}", "a" * 64, state, "2099-01-01", "Bevarad notering"))
        c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)", (uid(), approved, 1, "a" * 64, "approved", "owner", now()))
        c.execute("UPDATE schedule SET enabled=1,remaining=3,goal='Äldre automatisk research'")
        c.execute("UPDATE settings SET state=?,goal='Äldre marknadsresearch',total=230000,locked=80000,daily=5000,per_task=1000", (initial_state,))
        c.execute("DELETE FROM schema_migrations WHERE version=6")
        retained = {table: [tuple(row) for row in c.execute(f"SELECT * FROM {table}")] for table in ("owner", "approvals", "costs", "ideas", "files", "sources")}
        previous_focus_events = c.execute("SELECT COUNT(*) FROM events WHERE kind='project_focus'").fetchone()[0]
    initialize()
    with connect() as c:
        settings = dict(c.execute("SELECT * FROM settings").fetchone())
        assert settings["goal"] == MISSION
        assert settings["state"] == ("stopped" if initial_state == "stopped" else "paused")
        assert tuple(settings[key] for key in ("total", "locked", "daily", "per_task")) == (230000, 80000, 5000, 1000)
        assert c.execute("SELECT epoch FROM dispatch_control").fetchone()[0] == epoch + 1
        assert c.execute("SELECT enabled FROM schedule").fetchone()[0] == 0
        for status, task_id in tasks.items():
            task = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if status == "done":
                assert task["status"] == "done" and task["result"] == "sparat resultat"
            else:
                assert task["status"] == "blocked" and task["lease_until"] is None
                assert "fokusbyte" in task["error"]
        for name, reservation_id in reservations.items():
            reservation = c.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            assert reservation["status"] == ("released" if name == "prepared" else "unknown")
            assert reservation["amount"] == {"prepared": 40, "possible_send": 60, "orphan": 80, "prior_unknown": 100}[name]
            assert json.loads(reservation["metadata"]) == {"source": name}
        assert [r[0] for r in c.execute("SELECT state FROM runs")] == ["blocked", "blocked"]
        assert c.execute("SELECT status FROM proposals WHERE id=?", (pending,)).fetchone()[0] == "superseded"
        assert c.execute("SELECT status FROM proposals WHERE id=?", (approved,)).fetchone()[0] == "approved"
        assert {table: [tuple(row) for row in c.execute(f"SELECT * FROM {table}")] for table in retained} == retained
        assert c.execute("SELECT COUNT(*) FROM events WHERE kind='project_focus'").fetchone()[0] == previous_focus_events + 1
        assert "Äldre marknadsresearch" in c.execute("SELECT message FROM events WHERE kind='project_focus' ORDER BY id DESC LIMIT 1").fetchone()[0]
    initialize()
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM events WHERE kind='project_focus'").fetchone()[0] == previous_focus_events + 1
        assert c.execute("SELECT epoch FROM dispatch_control").fetchone()[0] == epoch + 1
        c.execute("UPDATE settings SET state='running'")
    assert worker.claim() is None  # Retired jobs are not revived by owner resume.
