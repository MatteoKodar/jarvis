from fastapi.testclient import TestClient
from jarvis.api import app
from jarvis.db import connect

def fresh_client():
    with connect(True) as c:
        c.execute('DELETE FROM owner')
        c.execute('DELETE FROM sessions')
    return TestClient(app, client=('127.0.0.1', 32100), headers={'origin':'http://127.0.0.1:8000'})

def test_first_run_creates_owner_and_authenticated_session(monkeypatch):
    monkeypatch.setenv('JARVIS_ORIGIN','http://127.0.0.1:8000')
    c=fresh_client()
    assert c.get('/api/setup').json()=={'needed':True,'allowed':True}
    result=c.post('/api/setup',json={'password':'chosen-test-password-123'})
    assert result.status_code==200
    assert result.json()['csrf']
    assert c.get('/api/state').status_code==200
    assert c.get('/api/setup').json()=={'needed':False,'allowed':False}
    assert c.post('/api/setup',json={'password':'replacement-password-123'}).status_code==409

def test_first_run_rejects_remote_origin_and_weak_password(monkeypatch):
    monkeypatch.setenv('JARVIS_ORIGIN','http://127.0.0.1:8000')
    c=fresh_client()
    assert c.post('/api/setup',json={'password':'short'}).status_code==422
    assert c.post('/api/setup',headers={'origin':'https://untrusted.example'},json={'password':'chosen-test-password-123'}).status_code==403
    remote=TestClient(app,client=('192.0.2.1',1234),headers={'origin':'http://127.0.0.1:8000'})
    assert remote.get('/api/setup').json()['allowed'] is False
    assert remote.post('/api/setup',json={'password':'chosen-test-password-123'}).status_code==403
    monkeypatch.setenv('JARVIS_ORIGIN','https://jarvis.example')
    assert c.get('/api/setup').json()['allowed'] is False
