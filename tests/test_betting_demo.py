"""Genomgående verifiering med syntetiska pengar och enbart temporära databaser."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from jarvis import betting_demo as core, betting_demo_service as service
from jarvis.db import connect, initialize
from jarvis.odds_lab import Action, Snapshot, analyze as legacy_analyze, digest
from jarvis.roles import ROLES
from jarvis.budget import RuleError

BASE = "/api/betting-demo/sessions"


def post(client, path="", **body):
    return client.post(BASE + path, json={"action_id": str(uuid4()), **body})


def create(client):
    client.post("/api/control", json={"state": "running"})
    response = post(client)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def view(client, sid):
    response = client.get(BASE + "/" + sid)
    assert response.status_code == 200, response.text
    return response.json()


def binding(client, sid):
    a = view(client, sid)["analysis"]
    return {"proposal_version": a["proposal_version"], "proposal_hash": a["proposal_hash"]}


def advance(client, sid, state):
    if state == "created":
        return
    assert post(client, f"/{sid}/analyze").status_code == 200
    if state in {"analyzed", "no_bets"}:
        return
    decision = "declined" if state == "declined" else "approved"
    assert post(client, f"/{sid}/decision", decision=decision, **binding(client, sid)).status_code == 200
    if state in {"approved", "declined"}:
        return
    assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 200
    if state == "settled":
        assert post(client, f"/{sid}/settle").status_code == 200


def db_counts(sid):
    with connect() as c:
        return {table: c.execute(f"SELECT COUNT(*) FROM betting_demo_{table} WHERE session_id=?", (sid,)).fetchone()[0]
                for table in ("costs", "bets", "events", "actions")}


def reference_scenario(initial=100000):
    frozen = core.build_scenario()
    frozen["initial_capital_ore"] = initial
    frozen["stake_ore"] = frozen["rules"]["stake_ore"] = 10000
    frozen["observations"] = frozen["observations"][:2]
    frozen["cost_definitions"] = frozen["cost_definitions"][:2]
    ids = {o["event_id"] for o in frozen["observations"]}
    frozen["settlement_data"] = {k: v for k, v in frozen["settlement_data"].items() if k in ids}
    for observation, cost in zip(frozen["observations"], frozen["cost_definitions"]):
        observation["data_cost_ore"] = cost["amount_ore"] = 500
        for i, quote in enumerate(observation["quotes"]):
            quote["odds"] = {"home": 20203, "draw": 34000, "away": 36000} if i == 0 else {"home": 18000, "draw": 45000, "away": 45000}
    return frozen


def no_bets(monkeypatch):
    frozen = core.build_scenario()
    for observation in frozen["observations"]:
        for quote in observation["quotes"]:
            quote["odds"]["home"] = 20000
    monkeypatch.setattr(service, "build_scenario", lambda: deepcopy(frozen))


def test_standard_scenario_matches_original_rules_and_expected_full_economy(client):
    original_budget = client.get("/api/state").json()["settings"]
    sid = create(client)
    assert view(client, sid)["summary"]["available_ore"] == 100000
    assert post(client, f"/{sid}/analyze").status_code == 200
    current = view(client, sid)
    assert len(current["observations"]) == 7
    assert len(current["analysis"]["proposals"]) == 4
    assert len([m for m in current["analysis"]["matches"] if not m["decision"]["selected"]]) == 3
    assert current["summary"]["simulated_cost_ore"] == 140
    assert current["summary"]["available_ore"] == 99860
    for observation, match in zip(current["observations"], current["analysis"]["matches"]):
        snapshot = Snapshot.model_validate(observation)
        old = legacy_analyze(snapshot, snapshot.captured_at, 99860)
        for key in ("selected", "paper_odds", "edge_bp", "outcome", "book", "reference_probability_ppm"):
            assert match["decision"].get(key) == old.get(key)
    assert post(client, f"/{sid}/decision", decision="approved", **binding(client, sid)).status_code == 200
    assert not view(client, sid)["bets"]
    assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 200
    assert view(client, sid)["summary"]["open_stake_ore"] == 4000
    assert view(client, sid)["summary"]["available_ore"] == 95860
    assert post(client, f"/{sid}/settle").status_code == 200
    result = view(client, sid)
    expected = {"initial_capital_ore": 100000, "game_profit_ore": 950, "simulated_cost_ore": 140,
                "net_ore": 810, "capital_ore": 100810, "open_stake_ore": 0, "available_ore": 100810,
                "total_stake_ore": 4000, "payout_ore": 4950, "bet_count": 4, "settled_count": 4,
                "won_count": 2, "lost_count": 2}
    assert result["summary"] == expected
    assert len(result["results"]) == 7
    initialize()
    assert view(client, sid) == result
    assert client.get("/api/state").json()["settings"]["spent"] == original_budget["spent"]
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM odds_lab_runs").fetchone()[0] == 0
    assert len(ROLES) == 10


@pytest.mark.parametrize("decline", [False, True])
def test_independent_reference_fixture_through_all_money_states(client, monkeypatch, decline):
    monkeypatch.setattr(service, "build_scenario", reference_scenario)
    sid = create(client)
    advance(client, sid, "analyzed")
    data = view(client, sid)
    assert [p["paper_odds"] for p in data["analysis"]["proposals"]] == [20000, 20000]
    assert data["summary"]["simulated_cost_ore"] == 1000
    assert data["summary"]["available_ore"] == 99000
    assert data["summary"]["open_stake_ore"] == 0
    assert post(client, f"/{sid}/decision", decision="declined" if decline else "approved", **binding(client, sid)).status_code == 200
    if not decline:
        assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 200
        middle = view(client, sid)["summary"]
        assert (middle["available_ore"], middle["open_stake_ore"], middle["capital_ore"]) == (79000, 20000, 99000)
        assert post(client, f"/{sid}/settle").status_code == 200
    final = view(client, sid)
    assert final["state"] == ("declined" if decline else "settled")
    for key, value in {"payout_ore": 0 if decline else 20000, "game_profit_ore": 0,
                       "simulated_cost_ore": 1000, "net_ore": -1000, "open_stake_ore": 0,
                       "capital_ore": 99000, "available_ore": 99000}.items():
        assert final["summary"][key] == value
    assert len(final["bets"]) == (0 if decline else 2)


@pytest.mark.parametrize("state", core.STATES)
@pytest.mark.parametrize("operation", ["analyze", "decision", "simulate", "settle"])
def test_state_machine_rejects_every_other_transition(client, monkeypatch, state, operation):
    if state == "no_bets":
        no_bets(monkeypatch)
    sid = create(client)
    advance(client, sid, state)
    before = view(client, sid)
    before_counts = db_counts(sid)
    extra = {}
    if operation in {"decision", "simulate"}:
        extra = binding(client, sid) if before["analysis"] else {"proposal_version": 1, "proposal_hash": "0" * 64}
    if operation == "decision":
        extra["decision"] = "approved"
    allowed = {"analyze": "created", "decision": "analyzed", "simulate": "approved", "settle": "simulated"}
    response = post(client, f"/{sid}/{operation}", **extra)
    assert response.status_code == (200 if allowed[operation] == state else 409)
    if response.status_code == 409:
        assert view(client, sid) == before
        assert db_counts(sid) == before_counts


def test_no_bets_charges_analysis_without_stakes_and_get_never_writes(client, monkeypatch):
    no_bets(monkeypatch)
    sid = create(client)
    advance(client, sid, "no_bets")
    data, counts = view(client, sid), db_counts(sid)
    assert data["state"] == "no_bets" and not data["bets"]
    assert data["summary"]["available_ore"] == 99860
    assert not data["analysis"]["proposals"]
    for _ in range(3):
        assert view(client, sid) == data
        assert client.get(BASE).status_code == 200
    assert db_counts(sid) == counts


def settle_after_reader_load(monkeypatch, session_ids):
    original_connect, original_load = service.connect, service._load
    readers, fired = [], []

    @contextmanager
    def tracked_connect(write=False):
        with original_connect(write) as c:
            if not write:
                readers.append(c)
            elif readers:
                assert c is not readers[0]
            yield c

    def interleaved_load(c, sid):
        row = original_load(c, sid)
        if readers and c is readers[0] and not fired:
            fired.append(sid)  # Engångshook; skrivarens egna _load får inte återtrigga.
            assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            for target in session_ids:
                assert service.settle(target, Action(action_id=str(uuid4()))) == {"id": target, "state": "settled"}
                # En tredje anslutning ser avräkningen: commit är klar innan läsaren fortsätter.
                with connect() as committed:
                    assert committed.execute("SELECT state FROM betting_demo_sessions WHERE id=?", (target,)).fetchone()[0] == "settled"
        return row

    monkeypatch.setattr(service, "connect", tracked_connect)
    monkeypatch.setattr(service, "_load", interleaved_load)
    return fired


def test_detail_keeps_one_snapshot_while_settlement_commits(client, monkeypatch):
    sid = create(client)
    advance(client, sid, "simulated")
    before = service.get_session(sid)
    assert before["state"] == "simulated" and before["summary"]["open_stake_ore"] == 4000
    assert {bet["state"] for bet in before["bets"]} == {"open"}
    assert "results" not in before
    fired = settle_after_reader_load(monkeypatch, [sid])

    assert service.get_session(sid) == before  # Hela svaret, inklusive summary, bets och history.
    assert fired == [sid]
    after = service.get_session(sid)
    assert after["state"] == "settled"
    assert after["summary"] == {"initial_capital_ore": 100000, "game_profit_ore": 950, "simulated_cost_ore": 140,
                                "net_ore": 810, "capital_ore": 100810, "open_stake_ore": 0, "available_ore": 100810,
                                "total_stake_ore": 4000, "payout_ore": 4950, "bet_count": 4, "settled_count": 4,
                                "won_count": 2, "lost_count": 2}
    assert sorted(bet["state"] for bet in after["bets"]) == ["lost", "lost", "won", "won"]
    assert [event["operation"] for event in after["history"]] == ["create", "analyze", "decision", "simulate", "settle"]
    assert after["history"][:-1] == before["history"]
    assert len(after["results"]) == 7
    results = {result["event_id"]: result for result in after["results"]}
    for bet in after["bets"]:
        assert bet["result"] == {key: value for key, value in results[bet["event_id"]].items() if key != "event_id"}
    assert after == view(client, sid)


def test_catalog_keeps_one_snapshot_across_all_sessions(client, monkeypatch):
    for _ in range(2):
        sid = create(client)
        advance(client, sid, "simulated")
    before = service.catalog()
    first, second = [session["id"] for session in before["sessions"]]
    assert [session["state"] for session in before["sessions"]] == ["simulated", "simulated"]
    # Läs A, committa A och därefter B, läs B: A-gammal/B-ny har aldrig existerat.
    fired = settle_after_reader_load(monkeypatch, [first, second])

    assert service.catalog() == before
    assert fired == [first]
    after = service.catalog()
    details = {sid: service.get_session(sid) for sid in (first, second)}
    assert after == {**before, "sessions": [
        {**session, "state": "settled", "summary": details[session["id"]]["summary"],
         "updated_at": details[session["id"]]["updated_at"]} for session in before["sessions"]]}
    assert all(detail["state"] == "settled" for detail in details.values())


@pytest.mark.parametrize("reader", ["detail", "catalog"])
@pytest.mark.parametrize("interrupted", [False, True])
def test_snapshot_read_never_writes_and_closes_even_on_error(client, monkeypatch, reader, interrupted):
    sid = create(client)
    advance(client, sid, "simulated")
    original_connect, original_load = service.connect, service._load
    connections, statements, changes = [], [], []

    @contextmanager
    def tracked_connect(write=False):
        assert not write
        with original_connect() as c:
            connections.append(c)
            c.set_trace_callback(statements.append)
            try:
                yield c
            finally:
                changes.append(c.total_changes)

    def fail_after_load(c, session_id):
        original_load(c, session_id)
        raise RuntimeError("test interrupted read")

    before = service.get_session(sid)
    monkeypatch.setattr(service, "connect", tracked_connect)
    if interrupted:
        monkeypatch.setattr(service, "_load", fail_after_load)
    read = (lambda: service.get_session(sid)) if reader == "detail" else service.catalog
    if interrupted:
        with pytest.raises(RuntimeError, match="test interrupted read"):
            read()
    else:
        read()
    assert len(connections) == 1 and changes == [0]
    assert statements[0] == "BEGIN"
    assert all(sql == "BEGIN" or sql.startswith("SELECT ") for sql in statements)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")
    monkeypatch.setattr(service, "connect", original_connect)
    monkeypatch.setattr(service, "_load", original_load)
    assert service.get_session(sid) == before


@pytest.mark.parametrize("operation,state", [("analyze", "created"), ("simulate", "approved"), ("settle", "simulated"), ("decision", "analyzed")])
def test_concurrent_different_ids_allow_exactly_one_transition(client, operation, state):
    sid = create(client)
    advance(client, sid, state)
    bodies = [{"action_id": str(uuid4())} for _ in range(2)]
    if operation in {"decision", "simulate"}:
        for body in bodies:
            body.update(binding(client, sid))
    if operation == "decision":
        bodies[0]["decision"], bodies[1]["decision"] = "approved", "declined"
    headers, cookies = dict(client.headers), dict(client.cookies)

    def submit(body):
        other = TestClient(service_app, headers=headers, cookies=cookies)
        try:
            return other.post(BASE + f"/{sid}/{operation}", json=body)
        finally:
            other.close()

    from jarvis.api import app as service_app
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, bodies))
    assert sorted(r.status_code for r in responses) == [200, 409]
    counts = db_counts(sid)
    assert counts["costs"] == 7
    assert counts["bets"] == (4 if operation in {"simulate", "settle"} else 0)
    if operation == "settle":
        assert view(client, sid)["summary"]["open_stake_ore"] == 0


@pytest.mark.parametrize("state", ["paused", "stopped"])
def test_saved_simulation_replay_after_stop_has_no_mutations(client, state):
    sid = create(client)
    advance(client, sid, "approved")
    body = {"action_id": str(uuid4()), **binding(client, sid)}
    first = client.post(BASE + f"/{sid}/simulate", json=body)
    assert first.status_code == 200
    client.post("/api/control", json={"state": state})
    before, counts = view(client, sid), db_counts(sid)
    assert client.post(BASE + f"/{sid}/simulate", json=body).json() == first.json()
    assert post(client, f"/{sid}/settle").status_code == 409
    assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 409
    assert client.post(BASE + f"/{sid}/simulate", json={**body, "proposal_hash": "0" * 64}).status_code == 409
    assert view(client, sid) == before and db_counts(sid) == counts


def test_pause_after_approval_prevents_new_simulation(client):
    sid = create(client)
    advance(client, sid, "approved")
    client.post("/api/control", json={"state": "paused"})
    assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 409
    assert view(client, sid)["state"] == "approved"
    assert not view(client, sid)["bets"]


def test_pause_and_write_share_the_database_serialization(client):
    sid = create(client)
    advance(client, sid, "approved")
    headers, cookies = dict(client.headers), dict(client.cookies)
    from jarvis.api import app

    def submit(path, body):
        c = TestClient(app, headers=headers, cookies=cookies)
        try:
            return c.post(path, json=body)
        finally:
            c.close()

    body = {"action_id": str(uuid4()), **binding(client, sid)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        write = pool.submit(submit, BASE + f"/{sid}/simulate", body)
        pause = pool.submit(submit, "/api/control", {"state": "paused"})
        result, stopped = write.result(), pause.result()
    assert stopped.status_code == 200
    assert result.status_code in {200, 409}
    assert len(view(client, sid)["bets"]) == (4 if result.status_code == 200 else 0)
    assert post(client).status_code == 409


def test_action_is_bound_to_session_operation_and_content(client):
    sid, other = create(client), create(client)
    action_id = str(uuid4())
    first = post(client, f"/{sid}/analyze", action_id=action_id)
    assert first.status_code == 200
    counts = db_counts(sid)
    assert post(client, f"/{sid}/analyze", action_id=action_id).json() == first.json()
    assert post(client, f"/{other}/analyze", action_id=action_id).status_code == 409
    assert post(client, f"/{sid}/settle", action_id=action_id).status_code == 409
    assert post(client, f"/{sid}/analyze").status_code == 409
    assert db_counts(sid) == counts


def test_insufficient_batch_capital_is_all_or_nothing(client, monkeypatch):
    monkeypatch.setattr(service, "build_scenario", lambda: reference_scenario(initial=15000))
    sid = create(client)
    advance(client, sid, "approved")
    before = view(client, sid)
    response = post(client, f"/{sid}/simulate", **binding(client, sid))
    assert response.status_code == 409 and "20000" in response.json()["detail"]
    assert view(client, sid) == before and not before["bets"]


def test_bad_scenario_cannot_spend_more_than_start_capital(client, monkeypatch):
    client.post("/api/control", json={"state": "running"})
    monkeypatch.setattr(service, "build_scenario", lambda: reference_scenario(initial=999))
    assert post(client).status_code == 409
    assert client.get(BASE).json()["sessions"] == []


@pytest.mark.parametrize("operation,state,table", [("analyze", "created", "costs"), ("simulate", "approved", "bets")])
def test_insert_failure_rolls_back_entire_batch(client, operation, state, table):
    sid = create(client)
    advance(client, sid, state)
    before, counts = view(client, sid), db_counts(sid)
    with connect(True) as c:
        c.execute(f"CREATE TRIGGER fail_demo BEFORE INSERT ON betting_demo_{table} WHEN NEW.event_id='syntetisk-2' BEGIN SELECT RAISE(ABORT,'test interruption'); END")
    extra = binding(client, sid) if operation == "simulate" else {}
    with pytest.raises(sqlite3.IntegrityError):
        post(client, f"/{sid}/{operation}", **extra)
    assert view(client, sid) == before and db_counts(sid) == counts


def test_partial_settlement_failure_rolls_back_every_result(client, monkeypatch):
    sid = create(client)
    advance(client, sid, "simulated")
    before, counts = view(client, sid), db_counts(sid)
    original, calls = service.settle_bet, []

    def fail_second(bet, result):
        calls.append(bet["event_id"])
        if len(calls) == 2:
            raise RuntimeError("test interruption")
        return original(bet, result)

    monkeypatch.setattr(service, "settle_bet", fail_second)
    with pytest.raises(RuntimeError):
        post(client, f"/{sid}/settle")
    assert view(client, sid) == before and db_counts(sid) == counts


def test_persisted_history_is_not_reinterpreted_by_new_code_or_scenario(client, monkeypatch):
    sid = create(client)
    advance(client, sid, "analyzed")
    before = view(client, sid)
    monkeypatch.setattr(service, "build_scenario", lambda: (_ for _ in ()).throw(AssertionError("no rebuild")))
    monkeypatch.setattr(service, "analyze_scenario", lambda *a: (_ for _ in ()).throw(AssertionError("no reanalysis")))
    # The v2 review is persisted too; continuing old work must never rebuild it.
    monkeypatch.setattr(service.demo_review, "build_scenario_v2", lambda *a: (_ for _ in ()).throw(AssertionError("no review rebuild")))
    monkeypatch.setattr(service.demo_review, "analyze_v2", lambda *a: (_ for _ in ()).throw(AssertionError("no review reanalysis")))
    assert post(client, f"/{sid}/decision", decision="approved", **binding(client, sid)).status_code == 200
    assert view(client, sid)["analysis"] == before["analysis"]
    assert post(client, f"/{sid}/simulate", **binding(client, sid)).status_code == 200
    assert post(client, f"/{sid}/settle").status_code == 200
    saved = view(client, sid)
    monkeypatch.setattr(service, "settle_bet", lambda *a: (_ for _ in ()).throw(AssertionError("no resettlement")))
    initialize()
    assert view(client, sid) == saved


def test_separate_capital_and_history_survive_new_round(client):
    first = create(client)
    advance(client, first, "settled")
    old = view(client, first)
    second = create(client)
    assert view(client, second)["summary"]["available_ore"] == 100000
    assert view(client, first) == old
    sessions = client.get(BASE).json()["sessions"]
    assert {s["id"] for s in sessions} == {first, second}
    assert "wallet" not in client.get(BASE).json()


def test_future_results_never_enter_analysis_and_are_hidden_in_every_public_stage(client, monkeypatch):
    scenario = core.build_scenario()
    original = core.analyze_scenario(core.analysis_input(scenario))
    changed = deepcopy(scenario)
    for result in changed["settlement_data"].values():
        result.update(home_score=91, away_score=92)
    another = core.analyze_scenario(core.analysis_input(changed))
    assert original == another
    with pytest.raises(ValidationError):
        core.ScenarioAnalysisInput.model_validate(scenario)
    captured = []
    original_engine = core.analyze_match

    def inspect(data):
        payload = data.model_dump(mode="json")
        assert set(payload) == {"observation", "simulated_analysis_at", "rules", "available_capital_ore"}
        assert "home_score" not in json.dumps(payload) and "settlement_data" not in payload
        captured.append(payload)
        return original_engine(data)

    monkeypatch.setattr(core, "analyze_match", inspect)
    sid = create(client)
    for target in ("created", "analyzed", "approved", "simulated"):
        if target == "analyzed":
            post(client, f"/{sid}/analyze")
        elif target == "approved":
            post(client, f"/{sid}/decision", decision="approved", **binding(client, sid))
        elif target == "simulated":
            post(client, f"/{sid}/simulate", **binding(client, sid))
        for response in (view(client, sid), client.get(BASE).json(), client.get("/api/state").json()):
            text = json.dumps(response)
            assert all(key not in text for key in ("home_score", "away_score", "settlement_data", "simulated_finished_at"))
    assert len(captured) == 7
    with pytest.raises(ValidationError):
        core.AnalysisInput(**captured[0], result={"home_score": 2})


def test_auth_demo_csrf_and_proposal_binding(client, monkeypatch):
    from jarvis.api import app
    stranger = TestClient(app)
    assert stranger.get(BASE).status_code == 401
    assert stranger.post(BASE, json={"action_id": str(uuid4())}).status_code == 401
    assert client.post(BASE, headers={"x-csrf-token": "bad"}, json={"action_id": str(uuid4())}).status_code == 403
    assert post(client, scenario={}).status_code == 422
    sid = create(client)
    advance(client, sid, "analyzed")
    assert post(client, f"/{sid}/decision", decision="approved", proposal_version=2, proposal_hash="0" * 64).status_code == 409
    monkeypatch.setenv("JARVIS_MODE", "LIVE")
    initialize()
    assert client.get(BASE).status_code == 401  # Separated LIVE DB has no authenticated test session.
    with pytest.raises(RuleError, match="DEMO"):
        service.catalog()


def test_demo_clock_never_changes_real_session_expiry(client):
    import time
    sid = create(client)
    assert view(client, sid)["observations"][0]["captured_at"].startswith("2025-")
    with connect() as c:
        assert c.execute("SELECT MIN(expires) FROM sessions").fetchone()[0] > time.time()
    with connect(True) as c:
        c.execute("UPDATE sessions SET expires=1")
    assert client.get(BASE).status_code == 401


@pytest.mark.parametrize("operation,state", [("analyze", "created"), ("decision", "analyzed"), ("settle", "simulated")])
def test_each_saved_transition_replays_exact_response_after_stop(client, operation, state):
    sid = create(client)
    advance(client, sid, state)
    body = {"action_id": str(uuid4())}
    if operation == "decision":
        body.update(decision="approved", **binding(client, sid))
    response = client.post(BASE + f"/{sid}/{operation}", json=body)
    assert response.status_code == 200
    client.post("/api/control", json={"state": "stopped"})
    before, counts = view(client, sid), db_counts(sid)
    assert client.post(BASE + f"/{sid}/{operation}", json=body).json() == response.json()
    if operation == "decision":
        assert client.post(BASE + f"/{sid}/{operation}", json={**body, "decision": "declined"}).status_code == 409
    assert view(client, sid) == before and db_counts(sid) == counts


def test_create_replay_after_pause_does_not_create_another_capital(client):
    client.post("/api/control", json={"state": "running"})
    body = {"action_id": str(uuid4())}
    response = client.post(BASE, json=body)
    client.post("/api/control", json={"state": "paused"})
    assert client.post(BASE, json=body).json() == response.json()
    assert len(client.get(BASE).json()["sessions"]) == 1


def test_created_session_uses_frozen_rules_when_global_policy_changes(client, monkeypatch):
    sid = create(client)
    # V2's outer hash also binds the review. Compare against a same-input control
    # analyzed before the policy change; the separate golden test pins legacy v1.
    control = create(client)
    assert post(client, f"/{control}/analyze").status_code == 200
    expected = view(client, control)["analysis"]
    monkeypatch.setitem(core.POLICY, "price_haircut_bp", 9000)
    assert post(client, f"/{sid}/analyze").status_code == 200
    saved = view(client, sid)["analysis"]
    assert saved["proposal_hash"] == expected["proposal_hash"]
    assert saved["proposals"] == expected["proposals"]
    assert saved == expected


def test_settlement_rounds_down_effective_odds_once():
    value = core.settle_bet({"outcome": "home", "stake_ore": 1001, "paper_odds": 24751},
                           {"status": "final", "home_score": 2, "away_score": 0})
    assert value == {"state": "won", "return_ore": 2477, "profit_ore": 1476}
