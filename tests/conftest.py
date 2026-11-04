import pytest
from fastapi.testclient import TestClient
from jarvis.db import initialize
from jarvis.auth import set_owner
from jarvis.api import app

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_MODE", "DEMO")
    monkeypatch.setenv("JARVIS_ORIGIN", "http://testserver")
    monkeypatch.setenv("JARVIS_SECURE_COOKIE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Use loopback for production startup validation; TestClient does not require lifespan here.
    initialize()
    set_owner("test-only-password-123")

@pytest.fixture
def client():
    c = TestClient(app)
    c.headers["origin"] = "http://testserver"
    response = c.post("/api/login", json={"password": "test-only-password-123"})
    assert response.status_code == 200
    c.headers["x-csrf-token"] = response.json()["csrf"]
    return c

