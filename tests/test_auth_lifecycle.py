"""Regressions for owner credential changes, using only the temporary test DB."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
import pytest

from jarvis import auth
from jarvis.api import app
from jarvis.db import connect
from jarvis.config import db_path


@pytest.fixture(autouse=True)
def temporary_database_only(isolated, tmp_path):
    assert db_path().parent == tmp_path.resolve()


def test_password_reset_rejects_login_that_verified_the_previous_owner(client, monkeypatch):
    old_password = 'test-only-password-123'
    new_password = 'new-synthetic-owner-password'
    verified, release = Event(), Event()
    original_hash = auth.hash_password

    def held_hash(password, salt):
        result = original_hash(password, salt)
        if password == old_password:
            verified.set()
            assert release.wait(10), 'Password-check gate was not released'
        return result

    monkeypatch.setattr(auth, 'hash_password', held_hash)
    contender = TestClient(app)
    contender.headers['origin'] = 'http://testserver'
    with ThreadPoolExecutor(max_workers=1) as executor:
        attempt = executor.submit(contender.post, '/api/login', json={'password': old_password})
        try:
            assert verified.wait(10), 'Login never verified its captured owner'
            auth.set_owner(new_password)
            with connect() as c:
                assert c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        finally:
            release.set()
        response = attempt.result(timeout=10)
    with connect() as c:
        session_count = c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
    print({'login_status': response.status_code, 'cookie_issued': 'set-cookie' in response.headers, 'sessions_after_reset': session_count})
    assert response.status_code == 401
    assert 'set-cookie' not in response.headers
    assert client.get('/api/session').status_code == 401  # Old owner session stays revoked.
    assert contender.get('/api/session').status_code == 401
    with connect() as c:
        assert c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        assert c.execute('SELECT attempts FROM login_attempts WHERE ip=?', ('testclient',)).fetchone()[0] == 1
    assert contender.post('/api/login', json={'password': new_password}).status_code == 200
    assert contender.get('/api/session').status_code == 200


def test_unchanged_owner_can_log_in_again(client):
    assert client.post('/api/login', json={'password': 'test-only-password-123'}).status_code == 200
    assert client.get('/api/session').status_code == 200




def test_replaced_owner_rejects_previous_password(client):
    auth.set_owner('another-synthetic-owner-password')
    assert client.post('/api/login', json={'password':'test-only-password-123'}).status_code == 401
    assert client.get('/api/session').status_code == 401
    assert client.post('/api/login', json={'password':'another-synthetic-owner-password'}).status_code == 200
    with connect() as c:
        assert c.execute('SELECT COUNT(*) FROM login_attempts').fetchone()[0] == 0


@pytest.mark.parametrize('password', [
    pytest.param('a' * 11, id='too-short'),
    pytest.param('a' * 257, id='too-long-ascii'),
    pytest.param('\u00e5' * 257, id='too-long-unicode'),
    pytest.param('\U0001f680' * 257, id='too-long-non-bmp'),
])
def test_invalid_owner_password_preserves_credentials_and_sessions(client, password):
    with connect() as c:
        before_owner = tuple(c.execute('SELECT * FROM owner').fetchone())
        before_sessions = [tuple(r) for r in c.execute('SELECT * FROM sessions ORDER BY token_hash')]
    with pytest.raises(ValueError, match='12.*256'):
        auth.set_owner(password)
    with connect() as c:
        assert tuple(c.execute('SELECT * FROM owner').fetchone()) == before_owner
        assert [tuple(r) for r in c.execute('SELECT * FROM sessions ORDER BY token_hash')] == before_sessions
    assert client.get('/api/session').status_code == 200
    assert client.post('/api/login', json={'password':'test-only-password-123'}).status_code == 200


@pytest.mark.parametrize('password', [
    pytest.param('a' * 12, id='minimum'),
    pytest.param('a' * 256, id='maximum'),
    pytest.param('\u00e5' * 256, id='maximum-unicode'),
    pytest.param('\U0001f680' * 256, id='maximum-non-bmp'),
])
def test_owner_password_boundaries_match_http_login(client, password):
    auth.set_owner(password)
    assert client.get('/api/session').status_code == 401
    assert client.post('/api/login', json={'password':password}).status_code == 200
    assert client.get('/api/session').status_code == 200
