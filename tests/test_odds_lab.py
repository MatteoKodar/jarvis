import ipaddress
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from jarvis import odds_service as service
from jarvis.api import app
from jarvis.budget import RuleError
from jarvis.db import connect, initialize
from jarvis.odds_lab import (POLICY, Cost, ImportSnapshot, Prices, Quote, Result, Snapshot,
                            Start, analyze, digest, example_snapshot, settlement)
from jarvis.roles import ROLES

AT = datetime(2026, 11, 3, 10, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo
    def local(host):
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return host == "localhost"
    def guarded_connect(sock, address):
        if not local(address[0]):
            raise AssertionError("Oddslabb får inte göra externa anslutningar.")
        return original_connect(sock, address)
    def guarded_lookup(host, *args, **kwargs):
        if not local(host):
            raise AssertionError("Oddslabb får inte göra externa namnuppslag.")
        return original_lookup(host, *args, **kwargs)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_lookup)
    monkeypatch.setattr(service, "clock", lambda: AT)
    with connect(True) as c:
        c.execute("UPDATE settings SET state='running'")


def start(kind="forward"):
    return service.start(Start(action_id=str(uuid4()), kind=kind, policy_hash=digest(POLICY)))["id"]


def snapshot(at=AT, event_id="match-1"):
    value = example_snapshot(at)
    value.update(event_id=event_id, home="Hemmalaget", away="Bortalaget")
    for quote in value["quotes"]:
        # Testreferenserna hämtas aldrig.
        quote["source_url"] = f"https://{quote['book']}.sports-reference.se/event"
    return value


def insert(run_id, data=None):
    body = ImportSnapshot(action_id=str(uuid4()), snapshot=Snapshot.model_validate(data or snapshot()))
    service.import_snapshot(run_id, body)
    return body


def result(event_id="match-1", home=2, away=0, status="final", **kwargs):
    return Result(action_id=str(uuid4()), event_id=event_id, market="1x2_90min", status=status,
                  home_score=None if status == "void" else home, away_score=None if status == "void" else away,
                  finished_at=AT + timedelta(hours=5), source_url="https://scores.sports-reference.se/event", **kwargs)


def test_synthetic_profit_is_labeled_and_never_unblocks_money():
    run_id = start("synthetic")
    report = service.get_run(run_id)
    stats = report["summary"]
    assert stats["snapshot_count"] == 7
    assert stats["signal_count"] == stats["settled_count"] == 4
    assert stats["won_count"] == stats["lost_count"] == 2
    assert stats["paper_profit_ore"] == 950
    assert stats["reported_cost_ore"] == 140
    assert stats["net_profit_ore"] == 810
    assert stats["max_realized_drawdown_ore"] >= 1000
    assert stats["status"] == "synthetic_only"
    assert stats["allows_real_money"] is False
    assert len(ROLES) == 10
    assert [m["decision"]["selected"] for m in stats["matches"]] == [True] * 4 + [False] * 3
    with connect() as c:
        for table in ("tasks", "operations", "reservations", "costs", "sources", "research_a0_runs"):
            assert c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_reference_excludes_target_and_applies_conservative_price():
    chosen = analyze(Snapshot.model_validate(snapshot()), AT, 100000)
    assert chosen["selected"] is True
    assert chosen["book"] == "kalla_1"
    assert chosen["book"] not in chosen["reference_books"]
    assert len(chosen["reference_books"]) == 3
    assert chosen["paper_odds"] == 24750
    assert 500 <= chosen["edge_bp"] <= 3000
    assert chosen["stake_ore"] == 1000


@pytest.mark.parametrize("case", ["stale", "future", "insufficient", "margin", "no_edge", "no_funds", "kickoff"])
def test_abstentions_are_explainable(case):
    value = snapshot()
    available = 100000
    if case == "stale":
        value["quotes"][0]["updated_at"] = (AT - timedelta(seconds=121)).isoformat()
    elif case == "future":
        value["quotes"][0]["updated_at"] = (AT + timedelta(seconds=1)).isoformat()
    elif case == "insufficient":
        value["quotes"] = value["quotes"][:3]
    elif case == "margin":
        value["quotes"][0]["odds"] = {k: 11000 for k in ("home", "draw", "away")}
    elif case == "no_edge":
        value["quotes"][0]["odds"]["home"] = 20000
    elif case == "no_funds":
        available = 999
    else:
        value["starts_at"] = AT.isoformat()
    assert analyze(Snapshot.model_validate(value), AT, available)["selected"] is False


@pytest.mark.parametrize("case", ["duplicate_book", "same_team", "extra_result", "wrong_market", "other_sport", "float_odds", "boolean_odds", "naive_time"])
def test_strict_input_and_one_market(case):
    value = snapshot()
    if case == "duplicate_book":
        value["quotes"][1]["book"] = value["quotes"][0]["book"]
    elif case == "same_team":
        value["away"] = value["home"].upper()
    elif case == "extra_result":
        value["result"] = "home"
    elif case == "wrong_market":
        value["market"] = "includes_extra_time"
    elif case == "other_sport":
        value["sport"] = "basketball"
    elif case == "float_odds":
        value["quotes"][0]["odds"]["home"] = 25000.0
    elif case == "boolean_odds":
        value["quotes"][0]["odds"]["home"] = True
    else:
        value["starts_at"] = "2026-11-03T13:00:00"
    with pytest.raises(ValidationError):
        Snapshot.model_validate(value)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "https://user:secret@host.se/event", "https://host.se/?apiKey=secret", "javascript:alert(1)"])
def test_source_reference_cannot_contain_credentials_or_non_http_urls(url):
    value = snapshot()
    value["quotes"][0]["source_url"] = url
    with pytest.raises(ValidationError):
        Snapshot.model_validate(value)


def test_forward_requires_fresh_pre_match_data_and_records_skip(monkeypatch):
    run_id = start()
    with pytest.raises(RuleError, match="exempeladresser"):
        insert(run_id, example_snapshot(AT))
    old = snapshot(AT - timedelta(seconds=61))
    with pytest.raises(RuleError, match="60 sekunder"):
        insert(run_id, old)
    future = snapshot(AT + timedelta(seconds=1))
    with pytest.raises(RuleError, match="60 sekunder"):
        insert(run_id, future)
    kicked = snapshot()
    kicked["starts_at"] = (AT + timedelta(seconds=30)).isoformat()
    with pytest.raises(RuleError, match="avspark"):
        insert(run_id, kicked)
    skipped = snapshot()
    skipped["quotes"] = skipped["quotes"][:3]
    insert(run_id, skipped)
    stats = service.get_run(run_id)["summary"]
    assert stats["snapshot_count"] == 1 and stats["signal_count"] == 0
    assert stats["status"] == "collecting"


def test_one_forward_series_and_match_cannot_be_reset_or_reidentified():
    run_id = start()
    with pytest.raises(RuleError, match="finns redan"):
        start()
    body = insert(run_id)
    assert service.import_snapshot(run_id, body) == {"id": run_id}
    renamed = snapshot(event_id="different-id")
    renamed["home"] = "  HEMMALAGET  "
    with pytest.raises(RuleError, match="Matchen är redan"):
        insert(run_id, renamed)
    changed = body.model_copy(deep=True)
    changed.snapshot.data_cost_ore = 1
    with pytest.raises(RuleError, match="bundet"):
        service.import_snapshot(run_id, changed)
    assert service.get_run(run_id)["summary"]["signal_count"] == 1


def test_same_match_cannot_be_reentered_with_shifted_time_or_reversed_teams():
    run_id = start()
    insert(run_id)
    value = snapshot(event_id="new-provider-id")
    value["starts_at"] = (AT + timedelta(hours=4)).isoformat()
    value["home"], value["away"] = value["away"], value["home"]
    with pytest.raises(RuleError, match="Matchen är redan"):
        insert(run_id, value)


def test_even_large_positive_series_and_complete_gates_cannot_enable_money(monkeypatch):
    run_id = start()
    insert(run_id)
    run = service.get_run(run_id)["run"]
    snapshot_record = deepcopy(run["records"][0])
    records = []
    # Ren sammanställningskontroll med 100 redan låsta, syntetiska internposter.
    # Detta får inte importeras som en verklig serie.
    for index in range(100):
        item = deepcopy(snapshot_record)
        item["payload"]["snapshot"]["event_id"] = f"sample-{index}"
        records.append(item)
        records.append({"kind": "result", "payload": {"result": {"event_id": f"sample-{index}"},
                        "settlement": {"state": "won", "profit_ore": 1475, "return_ore": 2475}}})
    run["records"] = records
    stats = service.summarize(run, AT + timedelta(days=31))
    assert stats["status"] == "positive_observation"
    assert all(stats["gates"].values())
    assert stats["allows_real_money"] is False
    assert stats["availability_verified"] is False
    assert stats["costs_verified"] is False


def test_concurrency_double_submit_persists_exactly_once():
    run_id = start()
    body = ImportSnapshot(action_id=str(uuid4()), snapshot=Snapshot.model_validate(snapshot()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: service.import_snapshot(run_id, body), range(2)))
    assert values[0] == values[1]
    assert service.get_run(run_id)["summary"]["signal_count"] == 1
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM odds_lab_records").fetchone()[0] == 1


def test_settlement_losses_draws_voids_persistence_and_costs(monkeypatch):
    run_id = start()
    body = insert(run_id)
    initial = service.get_run(run_id)["summary"]
    assert initial["available_ore"] == 99000 and initial["open_stake_ore"] == 1000
    with pytest.raises(RuleError, match="ordinarie matchtid"):
        service.record_result(run_id, result())
    monkeypatch.setattr(service, "clock", lambda: AT + timedelta(hours=6))
    loss = result(home=0, away=1)
    service.record_result(run_id, loss)
    service.record_result(run_id, loss)
    with pytest.raises(RuleError, match="redan registrerad"):
        service.record_result(run_id, result())
    service.record_cost(run_id, Cost(action_id=str(uuid4()), amount_ore=125, note="Allokerad dataavgift"))
    initialize()
    stats = service.get_run(run_id)["summary"]
    assert stats["lost_count"] == 1 and stats["open_count"] == 0
    assert stats["net_profit_ore"] == -1125
    assert stats["available_ore"] == 98875
    assert stats["max_realized_drawdown_ore"] == 1125
    decision = analyze(Snapshot.model_validate(snapshot()), AT, 100000)
    assert settlement(decision, result(home=1, away=1))["profit_ore"] == -1000
    assert settlement(decision, result(status="void"))["return_ore"] == 1000


def test_positive_small_sample_never_qualifies_and_window_cannot_be_extended(monkeypatch):
    run_id = start()
    insert(run_id)
    monkeypatch.setattr(service, "clock", lambda: AT + timedelta(hours=6))
    service.record_result(run_id, result())
    assert service.get_run(run_id)["summary"]["net_profit_ore"] > 0
    assert service.get_run(run_id)["summary"]["status"] == "collecting"
    monkeypatch.setattr(service, "clock", lambda: AT + timedelta(days=31))
    with pytest.raises(RuleError, match="observationsperioden"):
        insert(run_id, snapshot(AT + timedelta(days=31), "match-2"))
    stats = service.get_run(run_id)["summary"]
    assert stats["status"] == "insufficient_data"
    assert stats["allows_real_money"] is False


@pytest.mark.parametrize("state", ["paused", "stopped"])
def test_persistent_stop_blocks_writes_but_safe_retries_and_reads_work(state):
    run_id = start()
    body = insert(run_id)
    with connect(True) as c:
        c.execute("UPDATE settings SET state=?", (state,))
    initialize()
    assert service.import_snapshot(run_id, body) == {"id": run_id}
    assert service.get_run(run_id)["summary"]["signal_count"] == 1
    with pytest.raises(RuleError, match="Återuppta"):
        service.record_cost(run_id, Cost(action_id=str(uuid4()), amount_ore=1, note="Avgift"))


def test_live_cannot_read_or_mutate_lab_even_with_paid_flags(monkeypatch):
    run_id = start()
    monkeypatch.setenv("JARVIS_MODE", "LIVE")
    monkeypatch.setenv("JARVIS_PAID_ENABLED", "true")
    with pytest.raises(RuleError, match="DEMO"):
        service.get_run(run_id)
    with pytest.raises(RuleError, match="DEMO"):
        start()


@pytest.mark.parametrize("tamper", ["payload", "delete_last", "header"])
def test_integrity_detects_changed_or_missing_records(tamper):
    run_id = start("synthetic")
    with connect(True) as c:
        if tamper == "payload":
            c.execute("UPDATE odds_lab_records SET payload='{}' WHERE seq=(SELECT MIN(seq) FROM odds_lab_records)")
        elif tamper == "delete_last":
            c.execute("DELETE FROM odds_lab_records WHERE seq=(SELECT MAX(seq) FROM odds_lab_records)")
        else:
            c.execute("UPDATE odds_lab_runs SET created='2020-01-01T00:00:00+00:00'")
    with pytest.raises(RuleError, match="kontrollsumma"):
        service.get_run(run_id)


def test_rollbacks_stale_policy_and_no_fixture_mix():
    with pytest.raises(RuleError, match="ändrats"):
        service.start(Start(action_id=str(uuid4()), kind="forward", policy_hash="0" * 64))
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM odds_lab_runs").fetchone()[0] == 0
    run_id = start("synthetic")
    with pytest.raises(RuleError, match="blandas"):
        insert(run_id)
    assert service.get_run(run_id)["summary"]["snapshot_count"] == 7


def test_authenticated_api_csrf_schema_export_and_chunk_bound(client):
    anonymous = TestClient(app)
    assert anonymous.get("/api/odds-lab").status_code == 401
    anonymous.close()
    catalog = client.get("/api/odds-lab").json()
    body = {"action_id": str(uuid4()), "kind": "synthetic", "policy_hash": catalog["policy_hash"]}
    response = client.post("/api/odds-lab/runs", json=body)
    assert response.status_code == 200
    run_id = response.json()["id"]
    assert client.get(f"/api/odds-lab/runs/{run_id}/export").json()["summary"]["net_profit_ore"] == 810
    assert client.post("/api/odds-lab/runs", json={**body, "real_money_enabled": True}).status_code == 422
    assert client.get("/api/odds-lab/template").json()["sport"] == "football"
    assert client.post("/api/odds-lab/runs", content=iter([b" " * 26000, b" " * 26000])).status_code == 413
    client.headers["x-csrf-token"] = "wrong"
    assert client.post("/api/odds-lab/runs", json=body).status_code == 403
