import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from .db import connect

def hash_password(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

def set_owner(password):
    if not 12 <= len(password) <= 256:
        raise ValueError("Välj ett lösenord med 12–256 tecken.")
    salt = secrets.token_hex(16)
    with connect(True) as c:
        c.execute("INSERT INTO owner VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET salt=excluded.salt,password_hash=excluded.password_hash", (salt, hash_password(password, salt)))
        c.execute("DELETE FROM sessions")

def local_setup_allowed(request):
    origin = urlsplit(os.getenv("JARVIS_ORIGIN", "http://127.0.0.1:8000"))
    return bool(request.client and request.client.host in {"127.0.0.1", "::1"}
                and origin.scheme == "http" and origin.hostname in {"127.0.0.1", "localhost"})

def create_first_owner(request, password):
    origin_check(request)
    if not local_setup_allowed(request):
        raise HTTPException(403, "Första ägarkontot måste skapas lokalt på servern.")
    if not 12 <= len(password) <= 256:
        raise HTTPException(422, "Välj ett lösenord med 12–256 tecken.")
    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)
    with connect(True) as c:
        if c.execute("SELECT 1 FROM owner WHERE id=1").fetchone():
            raise HTTPException(409, "Ägarkontot finns redan. Logga in med ditt lösenord.")
        c.execute("INSERT INTO owner VALUES(1,?,?)", (salt, password_hash))

def origin_check(request):
    expected = os.getenv("JARVIS_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
    if request.headers.get("origin") != expected:
        raise HTTPException(403, "Felaktigt ursprung. Öppna den konfigurerade JARVIS-adressen.")

def authenticate(request: Request):
    token = request.cookies.get("jarvis_session", "")
    with connect() as c:
        session = c.execute("SELECT * FROM sessions WHERE token_hash=? AND expires>?", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not session:
        raise HTTPException(401, "Logga in som ägare.")
    if request.method not in {"GET", "HEAD"}:
        origin_check(request)
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf"]):
            raise HTTPException(403, "Ogiltigt CSRF-skydd. Ladda om sidan.")
    return dict(session)

def login(request, password):
    origin_check(request)
    ip = request.client.host if request.client else "local"
    # Commit failed attempts too, so the limit survives retries and restart.
    with connect(True) as c:
        attempt = c.execute("SELECT * FROM login_attempts WHERE ip=?", (ip,)).fetchone()
        if attempt and time.time()-attempt["since"] < 300 and attempt["attempts"] >= 5:
            raise HTTPException(429, "För många försök. Vänta fem minuter.")
        if not attempt or time.time()-attempt["since"] >= 300:
            c.execute("INSERT INTO login_attempts VALUES(?,1,?) ON CONFLICT(ip) DO UPDATE SET attempts=1,since=excluded.since", (ip, time.time()))
        else:
            c.execute("UPDATE login_attempts SET attempts=attempts+1 WHERE ip=?", (ip,))
        owner = c.execute("SELECT * FROM owner WHERE id=1").fetchone()
    if not owner:
        raise HTTPException(503, "Ägarkonto saknas. Kör python -m jarvis.cli owner.")
    if not hmac.compare_digest(hash_password(password, owner["salt"]), owner["password_hash"]):
        raise HTTPException(401, "Fel lösenord.")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with connect(True) as c:
        current_owner = c.execute("SELECT * FROM owner WHERE id=1").fetchone()
        if (not current_owner or current_owner["salt"] != owner["salt"]
                or current_owner["password_hash"] != owner["password_hash"]):
            raise HTTPException(401, "Ägarkontot ändrades under inloggningen. Logga in igen med aktuellt lösenord.")
        c.execute("DELETE FROM login_attempts WHERE ip=?", (ip,))
        c.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        c.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), csrf, time.time()+12*3600))
    return token, csrf

