"""En sparad begäran får aldrig kvittera annat innehåll som sparat."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from jarvis.api import app
from jarvis.db import connect, initialize, pack, uid
from jarvis import service


@pytest.mark.parametrize("path,body,changed", [
    ("/api/costs", {"amount": 100, "note": "Syntetisk kostnad"}, {"amount": 300}),
    ("/api/costs", {"amount": 100, "note": "Syntetisk kostnad"}, {"note": "Annat underlag"}),
    ("/api/rounds", {"goal": "Granska fotbollsdata A", "cap": 100}, {"goal": "Granska fotbollsdata B"}),
    ("/api/rounds", {"goal": "Granska fotbollsdata A", "cap": 100}, {"cap": 200}),
])
def test_changed_retry_is_conflict_and_keeps_original(client, path, body, changed):
    client.post("/api/control", json={"state": "running"})
    original = {**body, "action_id": uid()}
    assert client.post(path, json=original).status_code == 200
    before = service.snapshot()
    response = client.post(path, json={**original, **changed})
    assert response.status_code == 409
    assert "annat innehåll" in response.json()["detail"]
    after = service.snapshot()
    for key in ("costs", "tasks", "events", "settings"):
        assert after[key] == before[key]


@pytest.mark.parametrize("path,body", [
    ("/api/costs", {"amount": 100, "note": "Syntetisk kostnad"}),
    ("/api/rounds", {"goal": "Granska fotbollsdata", "cap": 100}),
])
@pytest.mark.parametrize("state", ["paused", "stopped"])
def test_identical_retry_survives_restart_and_stop(client, path, body, state):
    client.post("/api/control", json={"state": "running"})
    original = {**body, "action_id": uid()}
    first = client.post(path, json=original)
    assert first.status_code == 200
    initialize()
    client.post("/api/control", json={"state": state})
    before = service.snapshot()
    retry = client.post(path, json=original)
    assert retry.status_code == 200
    assert retry.json() == first.json()
    after = service.snapshot()
    for key in ("costs", "tasks", "events", "settings"):
        assert after[key] == before[key]


@pytest.mark.parametrize("path,bodies", [
    ("/api/costs", [{"amount": 100, "note": "Kostnad A"}, {"amount": 200, "note": "Kostnad B"}]),
    ("/api/rounds", [{"goal": "Granska fotbollsdata A", "cap": 100}, {"goal": "Granska fotbollsdata B", "cap": 200}]),
])
def test_concurrent_conflicting_requests_persist_only_the_winner(client, path, bodies):
    client.post("/api/control", json={"state": "running"})
    action_id = uid()
    cookies = dict(client.cookies)
    headers = dict(client.headers)

    def submit(body):
        other = TestClient(app, cookies=cookies, headers=headers)
        try:
            return other.post(path, json={**body, "action_id": action_id})
        finally:
            other.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, bodies))
    assert sorted(r.status_code for r in responses) == [200, 409]
    winner = bodies[next(i for i, response in enumerate(responses) if response.status_code == 200)]
    state = service.snapshot()
    if path == "/api/costs":
        assert len(state["costs"]) == 1
        assert state["costs"][0]["amount"] == winner["amount"]
        assert json.loads(state["costs"][0]["metadata"])["note"] == winner["note"]
    else:
        assert len(state["tasks"]) == 1
        assert state["tasks"][0]["title"] == winner["goal"]
        assert state["tasks"][0]["cap"] == winner["cap"]


@pytest.mark.parametrize("metadata", ["not-json", "[]", "{}"])
def test_unverifiable_cost_receipt_is_rejected_without_rewriting_it(client, metadata):
    body = {"action_id": uid(), "amount": 100, "note": "Syntetisk kostnad"}
    assert client.post("/api/costs", json=body).status_code == 200
    with connect(True) as c:
        c.execute("UPDATE costs SET metadata=? WHERE id=?", (metadata, body["action_id"]))
    assert client.post("/api/costs", json=body).status_code == 409
    with connect() as c:
        assert c.execute("SELECT metadata FROM costs WHERE id=?", (body["action_id"],)).fetchone()[0] == metadata


def test_other_operation_cannot_be_replayed_as_manual_cost(client):
    body = {"action_id": uid(), "amount": 100, "note": "Syntetisk kostnad"}
    assert client.post("/api/costs", json=body).status_code == 200
    with connect(True) as c:
        c.execute("UPDATE costs SET kind='estimate' WHERE id=?", (body["action_id"],))
    assert client.post("/api/costs", json=body).status_code == 409


def test_other_task_kind_cannot_be_replayed_as_owner_round(client):
    action_id = uid()
    with connect(True) as c:
        service.add_task(c, action_id=action_id, agent_id="critic", title="Granska fotbollsdata",
                         context=pack({}), criteria="Granska underlaget", cap=100, phase="review")
    response = client.post("/api/rounds", json={"action_id": action_id, "goal": "Granska fotbollsdata", "cap": 100})
    assert response.status_code == 409
    assert len(service.snapshot()["tasks"]) == 1
