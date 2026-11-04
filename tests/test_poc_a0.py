import json
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from jarvis import poc_service
from jarvis.api import app
from jarvis.budget import RuleError
from jarvis.db import connect, initialize
from jarvis.poc_a0 import (ClaimReview, Report, Review, SourcePackage, build_snapshot,
                           digest, examples, revise, suite, validate_citations)
from jarvis.roles import ROLES


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo
    def local(host):
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return host == "localhost"
    def guarded_connect(sock, address):
        if not local(address[0]):
            raise AssertionError("A0 får inte ansluta till externa nätverket.")
        return original_connect(sock, address)
    def guarded_lookup(host, *args, **kwargs):
        if not local(host):
            raise AssertionError("A0 får inte göra externa namnuppslag.")
        return original_lookup(host, *args, **kwargs)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_lookup)


def running():
    with connect(True) as c:
        c.execute("UPDATE settings SET state='running'")


def request_body():
    return {"action_id": str(uuid4()), "suite_hash": digest(suite())}


def test_snapshot_has_nine_reports_fifteen_simulated_steps_and_exact_roles():
    result = build_snapshot(ROLES)
    assert len(ROLES) == 10 == len(result["roles_snapshot"])
    assert result["report_count"] == 9
    assert result["simulated_steps"] == 15
    assert result["external_calls"] == result["cost_ore"] == 0
    assert result["model"] is None
    assert all(step["kind"] == "simulated" for report in result["reports"] for step in report["steps"])
    assert {r["flow"] for r in result["reports"]} == {"S1", "S2", "RK"}
    assert all(not r["final"]["support_verified"] for r in result["reports"])
    assert build_snapshot(ROLES) == result


def test_price_claim_removed_and_no_stale_recommendation_or_narrative_survives():
    snapshot = build_snapshot(ROLES)
    report = next(r for r in snapshot["reports"] if r["id"] == "A0-1-RK")
    assert report["original"]["recommendation"] == "billigt_experiment"
    assert report["final"]["recommendation"] == "avsta"
    assert report["final"]["missing_dependencies"] == ["P2"]
    assert report["original"]["claims"][1]["text"] not in report["final"]["text"]
    assert len(report["steps"]) == 2
    assert "report" in report["steps"][1]["input"]


def test_demo_does_not_always_make_critic_better():
    reports = {r["id"]: r for r in build_snapshot(ROLES)["reports"]}
    assert reports["A0-2-S2"]["final"]["recommendation"] == "vidare_research"
    assert reports["A0-2-RK"]["final"]["recommendation"] == "avsta"
    assert "felaktigt" in reports["A0-2-RK"]["review"]["claims"][0]["reason"]


@pytest.mark.parametrize("change", ["source", "quote", "position", "unicode_position"])
def test_invalid_citations_rejected_without_truncation(change):
    case = examples()[0]
    package = SourcePackage.model_validate(case["package"])
    report = Report.model_validate(case["report"])
    citation = report.claims[0].citations[0]
    if change == "source":
        citation.source_id = "UNKNOWN"
    elif change == "quote":
        citation.quote = "Ett citat som inte finns i källan."
    elif change == "position":
        citation.end_byte = 1000000
    else:
        citation.end_byte = len(package.sources[0].text)  # Characters are not UTF-8 byte offsets.
    with pytest.raises(ValueError):
        validate_citations(package, report)


def test_valid_citation_does_not_assert_semantic_truth():
    case = examples()[0]
    package, report = SourcePackage.model_validate(case["package"]), Report.model_validate(case["report"])
    validate_citations(package, report)
    final = revise(package, report, None)
    assert "bevisligen köpt" in final["text"]
    assert final["support_verified"] is False


@pytest.mark.parametrize("bad", ["duplicate", "missing", "unknown"])
def test_review_must_cover_each_claim_once(bad):
    case = examples()[0]
    checks = [ClaimReview.model_validate(c) for c in case["reviews"]["RK"]["claims"]]
    if bad == "duplicate":
        checks[1] = checks[0]
    elif bad == "missing":
        checks = checks[:1]
    else:
        checks[1].claim_id = "P8"
    with pytest.raises(ValueError):
        revise(SourcePackage.model_validate(case["package"]), Report.model_validate(case["report"]),
               Review(claims=checks, recommendation="avsta"))


def test_review_cannot_upgrade_and_hypotheses_cannot_support_recommendations():
    case = examples()[1]
    review = Review.model_validate(case["reviews"]["S2"])
    review.recommendation = "billigt_experiment"
    assert revise(SourcePackage.model_validate(case["package"]), Report.model_validate(case["report"]), review)["recommendation"] == "vidare_research"
    case["report"]["claims"][0]["kind"] = "hypotes"
    with pytest.raises(ValidationError):
        Report.model_validate(case["report"])


def test_reject_duplicate_sources_and_oversize_utf8_package():
    case = examples()[0]["package"]
    case["sources"][1]["id"] = "K1"
    with pytest.raises(ValidationError):
        SourcePackage.model_validate(case)
    case = examples()[0]["package"]
    case["sources"] = [{**case["sources"][0], "id": f"K{i}", "text": "å" * 8000} for i in range(5)]
    with pytest.raises(ValidationError, match="för stort"):
        SourcePackage.model_validate(case)


def test_requires_demo_even_when_paid_configuration_exists(monkeypatch):
    monkeypatch.setenv("JARVIS_MODE", "LIVE")
    monkeypatch.setenv("JARVIS_PAID_ENABLED", "true")
    with pytest.raises(RuleError, match="DEMO"):
        poc_service.start(**request_body())
    with pytest.raises(RuleError, match="DEMO"):
        poc_service.get_run("anything")


@pytest.mark.parametrize("state", ["paused", "stopped"])
def test_pause_and_persistent_stop_block_new_runs(state):
    with connect(True) as c:
        c.execute("UPDATE settings SET state=?", (state,))
    initialize()
    with pytest.raises(RuleError, match="Återuppta"):
        poc_service.start(**request_body())
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM research_a0_runs").fetchone()[0] == 0


def test_idempotence_persistence_export_and_no_business_data_changes(client, monkeypatch):
    running()
    body = request_body()
    # Historical archives are seeded by the pure helper, not by the retired public POST.
    envelope = poc_service.start(**body)
    assert digest(envelope["run"]) == envelope["sha256"]
    run_id = envelope["run"]["id"]
    initialize()
    with connect(True) as c:
        c.execute("UPDATE settings SET state='stopped'")
    monkeypatch.setattr(poc_service, "build_snapshot", lambda *args: pytest.fail("Får inte köras om."))
    assert poc_service.start(**body) == envelope
    archived = client.post("/api/research-poc/a0/runs", json=body)
    assert archived.status_code == 409 and "arkiverat" in archived.json()["detail"]
    assert client.get(f"/api/research-poc/a0/runs/{run_id}").json() == envelope
    exported = client.get(f"/api/research-poc/a0/runs/{run_id}/export")
    assert exported.json() == envelope
    assert "attachment" in exported.headers["content-disposition"]
    assert client.get("/api/research-poc/a0").json()["runs"][0]["id"] == run_id
    with connect() as c:
        for table in ("tasks", "costs", "reservations", "ideas", "sources"):
            assert c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM research_a0_runs").fetchone()[0] == 1


def test_concurrent_repeated_action_is_one_transaction_and_one_event():
    running()
    body = request_body()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: poc_service.start(**body), range(2)))
    assert results[0] == results[1]
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM research_a0_runs").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM events WHERE kind='research_a0'").fetchone()[0] == 1


def test_stale_suite_and_reused_action_with_changed_content_rejected():
    running()
    body = request_body()
    with pytest.raises(RuleError, match="ändrats"):
        poc_service.start(body["action_id"], "0" * 64)
    poc_service.start(**body)
    with pytest.raises(RuleError, match="bundet"):
        poc_service.start(body["action_id"], "0" * 64)


def test_failed_generation_rolls_back_without_partial_results(monkeypatch):
    running()
    def invalid(*args):
        raise ValueError("Ogiltigt underlag")
    monkeypatch.setattr(poc_service, "build_snapshot", invalid)
    with pytest.raises(ValueError):
        poc_service.start(**request_body())
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM research_a0_runs").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM events WHERE kind='research_a0'").fetchone()[0] == 0


def test_tampered_archive_is_detected_on_read():
    running()
    saved = poc_service.start(**request_body())
    with connect(True) as c:
        c.execute("UPDATE research_a0_runs SET payload=?", (json.dumps({"tampered": True}),))
    with pytest.raises(RuleError, match="kontrollsumma"):
        poc_service.get_run(saved["run"]["id"])


def test_api_authentication_csrf_schema_and_missing_run(client):
    anonymous = TestClient(app)
    try:
        assert anonymous.get("/api/research-poc/a0").status_code == 401
        assert anonymous.post("/api/research-poc/a0/runs", json=request_body()).status_code == 401
        assert anonymous.get("/api/research-poc/a0/runs/unknown/export").status_code == 401
    finally:
        anonymous.close()
    running()
    archived = client.post("/api/research-poc/a0/runs", json=request_body())
    assert archived.status_code == 409 and "arkiverat" in archived.json()["detail"]
    assert client.post("/api/research-poc/a0/runs", json={**request_body(), "mode": "LIVE"}).status_code == 422
    assert client.post("/api/research-poc/a0/runs", json={**request_body(), "action_id": "x" * 36}).status_code == 409
    assert client.get("/api/research-poc/a0/runs/unknown").status_code == 404
    assert client.get("/api/research-poc/a0/runs/unknown/export").status_code == 404
    client.headers["x-csrf-token"] = "wrong"
    assert client.post("/api/research-poc/a0/runs", json=request_body()).status_code == 403
