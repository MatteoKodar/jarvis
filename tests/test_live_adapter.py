"""Offline tests: real Runner -> Responses SDK -> HTTP client -> guarded mock transport."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
import httpx2
import pytest
from jarvis import live, research, service, worker, dispatch, external_http
from jarvis.auth import set_owner
from jarvis.budget import RuleError
from jarvis.db import initialize, connect, uid, pack, day, now
from jarvis.models import AgentResult
from jarvis.roles import ROLES


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo
    def connect_only_loopback(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("External connection forbidden in dispatch tests")
        return original_connect(sock, address)
    def lookup_only_loopback(host, *args, **kwargs):
        if host not in {"127.0.0.1", "::1", "localhost", None}:
            raise AssertionError("External DNS forbidden in dispatch tests")
        return original_lookup(host, *args, **kwargs)
    monkeypatch.setattr(socket.socket, "connect", connect_only_loopback)
    monkeypatch.setattr(socket, "getaddrinfo", lookup_only_loopback)


@pytest.fixture
def live_task(monkeypatch):
    # Historical transport coverage only. Production football roles have NO wiki tool.
    # Keep the archived integration's security/retry tests without granting runtime permission.
    monkeypatch.setitem(ROLES, "researcher", {**ROLES["researcher"], "tools": ["wikipedia_search"]})
    for k, v in {"JARVIS_MODE": "LIVE", "OPENAI_API_KEY": "test-key-never-sent", "JARVIS_MODEL": "test-model",
                 "JARVIS_PRICED_MODEL": "test-model", "JARVIS_INPUT_USD": "0.1", "JARVIS_OUTPUT_USD": "0.4",
                 "JARVIS_USD_SEK": "10", "JARVIS_PRICE_VERSION": "test-v1", "JARVIS_PAID_ENABLED": "true",
                 "JARVIS_RESEARCH_ENABLED": "true", "JARVIS_AGENT_MODELS": "{}"}.items():
        monkeypatch.setenv(k, v)
    initialize()
    set_owner("test-only-password-123")
    with connect(True) as c:
        c.execute("UPDATE settings SET state='running'")
    service.start_round("Fotbollstest utan nätverk", 500, uid())
    return worker.claim()


def work_task(task, role="researcher"):
    # Authority is changed in the test database, never merely in an incoming dictionary.
    with connect(True) as c:
        c.execute("UPDATE tasks SET agent_id=?,phase='work',context=? WHERE id=?",
                  (role, pack({"review_cap": 500}), task["id"]))
    return task


def response_data(output=None):
    return {"id": "resp_local", "object": "response", "created_at": 1, "status": "completed",
            "model": "test-model", "output": [{"id": "msg_local", "type": "message", "role": "assistant",
            "status": "completed", "content": [{"type": "output_text", "text": output or AgentResult(
                summary="Testadaptersvar", rationale="Lokalt transportsvar").model_dump_json(), "annotations": []}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
                      "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}


@pytest.fixture
def wire(monkeypatch):
    calls = {"model": [], "research": []}
    def model(request):
        calls["model"].append(request)
        assert request.url.host == "api.openai.com"
        return httpx2.Response(200, json=response_data())
    def wiki(request):
        calls["research"].append(request)
        assert request.url.host == "sv.wikipedia.org"
        with connect() as c:
            assert c.execute("SELECT status FROM reservations").fetchone()[0] == "held"
        return httpx.Response(200, json={"query": {"search": [{"pageid": 123, "title": "Testkälla",
                                               "snippet": "Ett <b>utdrag</b> med bakgrund."}]}})
    monkeypatch.setattr(external_http, "model_transport", lambda: httpx2.MockTransport(model))
    monkeypatch.setattr(external_http, "research_transport", lambda: httpx.MockTransport(wiki))
    return calls


def operations():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM operations ORDER BY kind")]


def reservations():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM reservations")]


def test_success_real_sdk_records_token_price_fx_and_rejects_repeat(live_task, wire):
    result = asyncio.run(live.run(live_task))
    assert result.summary == "Testadaptersvar"
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert len(wire["model"]) == 1 and not wire["research"]  # 2 adapter calls, 1 send
    assert reservations()[0]["status"] == "settled"
    assert operations()[0]["state"] == "completed"
    s = service.snapshot()
    assert len(s["costs"]) == 1 and "test-v1" in s["costs"][0]["metadata"]
    assert "test-key-never-sent" not in pack(operations()) + pack(reservations())


@pytest.mark.parametrize("failure", ["429", "503", "401", "conversation_locked", "connect", "timeout", "truncated", "redirect", "malformed", "no_usage", "incomplete"])
def test_real_sdk_one_http_attempt_and_unknown_after_failure(live_task, monkeypatch, wire, failure):
    calls = []
    class BrokenStream(httpx2.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"id":"resp_local",'
            raise httpx2.ReadError("locally interrupted body")
    def fail(request):
        calls.append(request)
        if failure in {"429", "503", "401"}:
            return httpx2.Response(int(failure), headers={"retry-after": "0", "x-should-retry": "true"}, json={"error": {"message": "local error", "type": "test"}})
        if failure == "conversation_locked":
            return httpx2.Response(409, json={"error": {"message": "Conversation is locked", "code": "conversation_locked", "type": "invalid_request_error"}})
        if failure == "connect":
            raise httpx2.ConnectError("local connect failure", request=request)
        if failure == "timeout":
            raise httpx2.ReadTimeout("local timeout", request=request)
        if failure == "truncated":
            return httpx2.Response(200, stream=BrokenStream())
        if failure == "redirect":
            return httpx2.Response(307, headers={"location": "https://api.openai.com/v1/responses"})
        data = response_data("not JSON" if failure == "malformed" else None)
        if failure == "no_usage":
            data.pop("usage")
        if failure == "incomplete":
            data["status"] = "incomplete"
        return httpx2.Response(200, json=data)
    monkeypatch.setattr(external_http, "model_transport", lambda: httpx2.MockTransport(fail))
    with pytest.raises(Exception):
        asyncio.run(live.run(live_task))
    initialize()  # same persisted identity after database reopen
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert len(calls) == 1  # 2 adapter calls, 1 HTTP send, real SDK layers
    assert operations()[0]["state"] == "unknown"
    assert reservations()[0]["status"] == "unknown"
    assert not service.snapshot()["costs"]


@pytest.mark.parametrize("adapter", [live.run, research.search])
def test_direct_demo_denied_with_otherwise_live_configuration(live_task, monkeypatch, wire, adapter):
    monkeypatch.setenv("JARVIS_MODE", "DEMO")
    with pytest.raises(RuleError, match="DEMO"):
        asyncio.run(adapter(live_task))
    assert not wire["model"] and not wire["research"]


@pytest.mark.parametrize("key,value", [("JARVIS_PAID_ENABLED", "false"), ("JARVIS_RESEARCH_ENABLED", "false"),
                                        ("JARVIS_PRICE_VERSION", ""), ("JARVIS_PRICED_MODEL", "different"),
                                        ("JARVIS_INPUT_USD", "NaN"), ("JARVIS_OUTPUT_USD", "-1"),
                                        ("JARVIS_AGENT_MODELS", '{"ceo":"other-model"}')])
@pytest.mark.parametrize("adapter", [live.run, research.search])
def test_missing_activation_or_price_denies_direct_calls(live_task, monkeypatch, wire, key, value, adapter):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuleError):
        asyncio.run(adapter(live_task))
    assert not wire["model"] and not wire["research"] and not reservations()


def test_unverified_sdk_fails_closed(live_task, monkeypatch, wire):
    monkeypatch.setattr(external_http, "version", lambda name: "unreviewed")
    with pytest.raises(RuleError, match="granskning"):
        asyncio.run(live.run(live_task))
    assert not wire["model"] and not reservations()


@pytest.mark.parametrize("status", ["queued", "done", "blocked", "review", "approval"])
def test_database_status_rejects_forged_running_handle(live_task, wire, status):
    with connect(True) as c:
        c.execute("UPDATE tasks SET status=? WHERE id=?", (status, live_task["id"]))
    live_task["status"] = "running"
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert not wire["model"] and not reservations()


def test_forged_role_and_cap_do_not_grant_research(live_task, wire):
    work_task(live_task, "developer")
    live_task.update(agent_id="researcher", cap=999999, phase="work")
    with pytest.raises(RuleError):
        asyncio.run(research.search(live_task))
    assert not wire["research"]
    with pytest.raises(RuleError):
        dispatch.prepare(live_task, "free.any-url")


@pytest.mark.parametrize("change", ["missing_run", "old_run", "run_done", "expired_lease", "wrong_phase"])
def test_invalid_current_run_or_role_phase(live_task, wire, change):
    with connect(True) as c:
        if change == "run_done":
            c.execute("UPDATE runs SET state='done'")
        if change == "expired_lease":
            c.execute("UPDATE tasks SET lease_until=0")
        if change == "wrong_phase":
            c.execute("UPDATE tasks SET agent_id='developer'")
    if change == "missing_run":
        live_task.pop("run_id")
    if change == "old_run":
        live_task["run_id"] = uid()
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert not wire["model"]


@pytest.mark.parametrize("limit", ["task", "total", "daily", "locked", "per_task"])
def test_model_budget_before_research(live_task, wire, limit):
    work_task(live_task)
    with connect(True) as c:
        if limit == "task":
            c.execute("UPDATE tasks SET cap=0")
        else:
            c.execute({"total": "UPDATE settings SET total=locked", "daily": "UPDATE settings SET daily=0",
                       "locked": "UPDATE settings SET locked=total", "per_task": "UPDATE settings SET per_task=0"}[limit])
    live_task["cap"] = 50000
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert not wire["model"] and not wire["research"] and not reservations()


def test_research_model_shared_reservation_and_source_metadata(live_task, wire):
    work_task(live_task)
    asyncio.run(live.run(live_task))
    assert len(wire["research"]) == len(wire["model"]) == 1
    assert len(reservations()) == 1 and reservations()[0]["status"] == "settled"
    assert all(op["state"] == "completed" for op in operations())
    source = service.snapshot()["sources"][0]
    assert source["retrieved"] and source["origin"] == "wikipedia:sv:123"
    assert source["claim"] == "Ett utdrag med bakgrund."
    assert source["url"] == "https://sv.wikipedia.org/?curid=123"


def test_standalone_research_cancels_unused_model_but_keeps_own_completion(live_task, wire):
    work_task(live_task)
    asyncio.run(research.search(live_task))
    with pytest.raises(RuleError):
        asyncio.run(research.search(live_task))
    assert len(wire["research"]) == 1 and not wire["model"]
    assert [op["state"] for op in operations()] == ["cancelled", "completed"]
    assert reservations()[0]["status"] == "released"


def test_concurrent_workers_one_model_send(live_task, monkeypatch):
    entered, release, second_done = threading.Event(), threading.Event(), threading.Event()
    sends = []
    async def delayed(request):
        sends.append(request)
        entered.set()
        assert await asyncio.to_thread(release.wait, 20)
        return httpx2.Response(200, json=response_data())
    monkeypatch.setattr(external_http, "model_transport", lambda: httpx2.MockTransport(delayed))
    def duplicate():
        assert entered.wait(20)
        try:
            with pytest.raises(RuleError):
                asyncio.run(live.run(live_task))
        finally:
            second_done.set()
            release.set()
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(asyncio.run, live.run(live_task))
        second = pool.submit(duplicate)
        second.result(30)
        assert second_done.is_set()
        assert first.result(30).summary == "Testadaptersvar"
    assert len(sends) == 1 and len(reservations()) == 1
    assert len(service.snapshot()["costs"]) == 1


def test_changed_input_same_identity_rejected(live_task, wire):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "original")
    with pytest.raises(RuleError):
        dispatch.bind(oid, "changed")
    with connect(True) as c:
        c.execute("UPDATE tasks SET context='ändrat underlag'")
    with pytest.raises(RuleError, match="ändrat"):
        dispatch.prepare(live_task)
    with pytest.raises(RuleError):
        dispatch.authorize(oid, "fake-transport", dispatch.digest("original"))
    assert not wire["model"]
    dispatch.abort(oid)
    assert reservations()[0]["status"] == "released"


def test_stop_before_prepare_and_after_reservation_resume_never_revives(live_task, wire):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "bound")
    with connect(True) as c:
        dispatch.control(c, "stopped")
    assert reservations()[0]["status"] == "released"
    assert operations()[0]["state"] == "cancelled"
    with pytest.raises(RuleError):
        dispatch.authorize(oid, "http", dispatch.digest("bound"))
    with connect(True) as c:
        dispatch.control(c, "running")
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert not wire["model"]


def test_persistent_stop_serializes_before_transport_authorization(live_task, monkeypatch, wire):
    original = dispatch.authorize
    def stop_first(*args):
        with connect(True) as c:
            dispatch.control(c, "stopped")
        return original(*args)
    monkeypatch.setattr(dispatch, "authorize", stop_first)
    with pytest.raises(Exception):
        asyncio.run(live.run(live_task))
    assert not wire["model"] and reservations()[0]["status"] == "released"


def test_stop_after_authorization_is_unknown_even_if_authorized_send_proceeds(live_task, monkeypatch, wire):
    original = dispatch.authorize
    def stop_after(*args):
        original(*args)
        with connect(True) as c:
            dispatch.control(c, "stopped")
    monkeypatch.setattr(dispatch, "authorize", stop_after)
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert len(wire["model"]) == 1
    assert operations()[0]["state"] == reservations()[0]["status"] == "unknown"


def test_cancelled_real_sdk_transport_keeps_unknown(live_task, monkeypatch):
    async def scenario():
        entered = asyncio.Event()
        async def delayed(request):
            entered.set()
            await asyncio.Event().wait()
        monkeypatch.setattr(external_http, "model_transport", lambda: httpx2.MockTransport(delayed))
        job = asyncio.create_task(live.run(live_task))
        await entered.wait()
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
    asyncio.run(scenario())
    assert reservations()[0]["status"] == operations()[0]["state"] == "unknown"


def test_crash_after_marker_zero_http_restart_and_manual_reconciliation(live_task, client, wire):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "bound")
    dispatch.authorize(oid, "not-yet-sent", dispatch.digest("bound"))
    # Simulated process loss: no adapter finally executes. Lease expiry is deterministic.
    with connect(True) as c:
        c.execute("UPDATE tasks SET lease_until=0")
    initialize()
    assert worker.claim() is None
    assert reservations()[0]["status"] == operations()[0]["state"] == "unknown"
    rid = reservations()[0]["id"]
    assert client.post(f"/api/reservations/{rid}/reconcile", json={"amount": 0, "note": "Manuellt avstämt lokalt test"}).status_code == 200
    assert client.post("/api/control", json={"state": "stopped"}).status_code == 200
    assert client.post("/api/control", json={"state": "running"}).status_code == 200
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert operations()[0]["state"] == "unknown" and reservations()[0]["status"] == "reconciled"
    assert not wire["model"]


def test_other_process_cannot_resend_authorized_operation(live_task, wire):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "bound")
    dispatch.authorize(oid, "http", dispatch.digest("bound"))
    code = """
import asyncio,json,socket,sys
from jarvis import live
from jarvis.budget import RuleError
original_connect=socket.socket.connect
original_lookup=socket.getaddrinfo
def guarded_connect(sock,address):
    assert isinstance(address,tuple) and address[0] in {'127.0.0.1','::1','localhost'}, 'external forbidden'
    return original_connect(sock,address)
def guarded_lookup(host,*args,**kwargs):
    assert host in {'127.0.0.1','::1','localhost',None}, 'DNS forbidden'
    return original_lookup(host,*args,**kwargs)
socket.socket.connect=guarded_connect
socket.getaddrinfo=guarded_lookup
try:
    asyncio.run(live.run(json.loads(sys.argv[1])))
except RuleError:
    print('blocked')
else:
    raise AssertionError('replayed')
"""
    env = os.environ | {"PYTHONPATH": str(Path("backend").resolve()), "PYTHON_DOTENV_DISABLED": "1"}
    result = subprocess.run([sys.executable, "-c", code, pack(live_task)], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "blocked" and not wire["model"]
    dispatch.abort(oid)
    assert reservations()[0]["status"] == "unknown"


def test_pause_allows_existing_run_but_no_new_claim(live_task, wire):
    with connect(True) as c:
        dispatch.control(c, "paused")
    assert worker.claim() is None
    assert asyncio.run(live.run(live_task)).summary == "Testadaptersvar"
    assert len(wire["model"]) == 1


def test_early_size_check_before_search_and_reservation(live_task, wire):
    work_task(live_task)
    with connect(True) as c:
        c.execute("UPDATE tasks SET context=?", ("å" * 65536,))
    with pytest.raises(RuleError, match="stort"):
        asyncio.run(live.run(live_task))
    assert not wire["research"] and not wire["model"] and not reservations()


def test_final_size_rejection_preserves_completed_research(live_task, wire):
    work_task(live_task)
    # Real boundary: the known base fits with 100 bytes remaining; saved sources exceed it.
    with connect(True) as c:
        task = dict(c.execute("SELECT * FROM tasks WHERE id=?", (live_task["id"],)).fetchone())
        text = dispatch.payload(task, [])
        used = len((text + dispatch.ROLES[task["agent_id"]]["instructions"] + pack(AgentResult.model_json_schema())).encode("utf-8")) + 16384
        c.execute("UPDATE tasks SET context=?", (task["context"] + "x" * (dispatch.MAX_INPUT - used - 100),))
    with pytest.raises(RuleError, match="stort"):
        asyncio.run(live.run(live_task))
    assert len(wire["research"]) == 1 and not wire["model"]
    assert [op["state"] for op in operations()] == ["cancelled", "completed"]
    assert reservations()[0]["status"] == "released"


def test_migration_preserves_owner_decision_cost_and_unknown_reservation(client):
    assert client.post("/api/control", json={"state": "running"}).status_code == 200
    service.start_round("Undersök lokalt underlag", 500, uid())
    task = worker.claim()
    asyncio.run(worker.execute(task))
    proposal = service.snapshot()["proposals"][0]
    assert client.post(f"/api/proposals/{proposal['id']}/decision", json={"version": proposal["version"], "digest": proposal["digest"], "decision": "approved", "note": "Testbeslut"}).status_code == 200
    with connect(True) as c:
        c.execute("INSERT INTO reservations VALUES(?,?,?,?,?,?)", (uid(), task["id"], 30, day(), "unknown", pack({"original": "v1"})))
        c.execute("INSERT INTO costs VALUES(?,?,?,?,?,?,?,?)", (uid(), task["id"], "ceo", 10, day(), "estimate", "{}", now()))
        before = {table: [tuple(r) for r in c.execute(f"SELECT * FROM {table}")] for table in ("approvals", "proposals", "costs", "reservations")}
        c.execute("DROP TABLE operations")
        c.execute("DROP TABLE dispatch_control")
        c.execute("ALTER TABLE runs DROP COLUMN dispatch_epoch")
        c.execute("DELETE FROM schema_migrations WHERE version=4")
    initialize()
    with connect() as c:
        after = {table: [tuple(r) for r in c.execute(f"SELECT * FROM {table}")] for table in before}
        assert c.execute("SELECT dispatch_epoch FROM runs").fetchone()[0] is None
    assert after == before


def test_real_transport_retry_settings_and_no_redirect_defaults():
    for factory in (external_http.model_transport, external_http.research_transport):
        transport = factory()
        assert transport._pool._retries == 0
        assert transport._pool._http2 is False
        assert transport._pool._max_keepalive_connections == 0
        asyncio.run(transport.aclose())
    assert external_http.verified_versions() == external_http.VERIFIED


@pytest.mark.parametrize("failure", ["429", "503", "connect", "timeout", "truncated", "redirect"])
def test_wikipedia_failure_one_free_send_releases_unused_model(live_task, monkeypatch, wire, failure):
    work_task(live_task)
    sends = []
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"query":'
            raise httpx.ReadError("local incomplete reply")
    def fail(request):
        sends.append(request)
        if failure in {"429", "503"}:
            return httpx.Response(int(failure), headers={"retry-after": "0"})
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://sv.wikipedia.org/w/api.php"})
        if failure == "connect":
            raise httpx.ConnectError("local failure")
        if failure == "timeout":
            raise httpx.ReadTimeout("local failure")
        return httpx.Response(200, stream=BrokenStream())
    monkeypatch.setattr(external_http, "research_transport", lambda: httpx.MockTransport(fail))
    with pytest.raises(Exception):
        asyncio.run(live.run(live_task))
    with pytest.raises(RuleError):
        asyncio.run(live.run(live_task))
    assert len(sends) == 1 and not wire["model"]
    assert [op["state"] for op in operations()] == ["cancelled", "unknown"]
    assert reservations()[0]["status"] == "released"


@pytest.mark.parametrize("failure", ["connect", "timeout"])
def test_real_httpcore_transport_does_not_retry_connection(live_task, monkeypatch, failure):
    import httpcore2
    transport = external_http.model_transport()
    attempts = []
    class OfflineNetwork:
        async def connect_tcp(self, **kwargs):
            attempts.append(kwargs["host"])
            raise (httpcore2.ConnectError if failure == "connect" else httpcore2.ConnectTimeout)("local connect failure")
    transport._pool._network_backend = OfflineNetwork()
    monkeypatch.setattr(external_http, "model_transport", lambda: transport)
    with pytest.raises(Exception):
        asyncio.run(live.run(live_task))
    assert len(attempts) == 1
    assert reservations()[0]["status"] == "unknown"


def test_same_operation_transport_authorized_once_under_contention(live_task):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "bound")
    gate = threading.Barrier(2)
    def authorize():
        gate.wait(timeout=20)
        try:
            dispatch.authorize(oid, "http", dispatch.digest("bound"))
            return True
        except RuleError:
            return False
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: authorize(), range(2)))
    assert sorted(results) == [False, True]
    assert len(reservations()) == 1
    dispatch.abort(oid)
    assert reservations()[0]["status"] == "unknown"


def test_price_change_after_prepare_cancels_before_any_send(live_task, monkeypatch, wire):
    oid, _ = dispatch.prepare(live_task)
    dispatch.bind(oid, "bound")
    monkeypatch.setenv("JARVIS_PRICE_VERSION", "changed-price")
    with pytest.raises(RuleError):
        dispatch.authorize(oid, "http", dispatch.digest("bound"))
    dispatch.abort(oid)
    assert reservations()[0]["status"] == "released" and not wire["model"]


def test_restart_recovery_releases_proven_pre_marker_reservation(live_task):
    dispatch.prepare(live_task)
    with connect(True) as c:
        c.execute("UPDATE tasks SET lease_until=0")
    initialize()
    assert worker.claim() is None
    assert operations()[0]["state"] == "cancelled"
    assert reservations()[0]["status"] == "released"


def test_compressed_response_processed_once_without_second_decoding(live_task, monkeypatch):
    import gzip
    calls = []
    def reply(request):
        calls.append(request)
        return httpx2.Response(200, headers={"content-encoding": "gzip"},
                               content=gzip.compress(json.dumps(response_data()).encode("utf-8")))
    monkeypatch.setattr(external_http, "model_transport", lambda: httpx2.MockTransport(reply))
    assert asyncio.run(live.run(live_task)).summary == "Testadaptersvar"
    assert len(calls) == 1 and reservations()[0]["status"] == "settled"


def test_transport_hash_must_match_previously_bound_payload(live_task):
    oid, _ = dispatch.prepare(live_task)
    with pytest.raises(RuleError):
        dispatch.authorize(oid, "http", None)
    dispatch.bind(oid, "original")
    with pytest.raises(RuleError):
        dispatch.authorize(oid, "http", dispatch.digest("changed"))
    assert operations()[0]["state"] == "prepared"
    dispatch.abort(oid)
    assert reservations()[0]["status"] == "released"


def test_late_worker_completion_after_stop_resume_does_not_create_proposal(live_task):
    with connect(True) as c:
        dispatch.control(c, "stopped")
        dispatch.control(c, "running")
    worker.finish(live_task, AgentResult(summary="Sent svar", rationale="Lokalt test"))
    with connect() as c:
        assert c.execute("SELECT status FROM tasks WHERE id=?", (live_task["id"],)).fetchone()[0] == "blocked"
        assert c.execute("SELECT COUNT(*) FROM proposals").fetchone()[0] == 0
