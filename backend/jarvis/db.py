import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .config import ROOT, db_path
from .roles import ROLES

def now():
    return datetime.now(timezone.utc).isoformat()

def day():
    return datetime.now(ZoneInfo("Europe/Stockholm")).date().isoformat()

def uid():
    return uuid.uuid4().hex

def pack(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

@contextmanager
def connect(write=False):
    conn = sqlite3.connect(db_path(), timeout=20, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=20000")
    try:
        if write:
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        if write:
            conn.commit()
    except Exception:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()

def _execute_script(c, script):
    # executescript implicitly commits; execute complete statements to retain our lock.
    start = 0
    for end, char in enumerate(script):
        if char == ";" and sqlite3.complete_statement(script[start:end + 1]):
            c.execute(script[start:end + 1])
            start = end + 1
    # Execute the remainder too: comments are harmless, invalid SQL must fail.
    if script[start:].strip():
        c.execute(script[start:])

def _enable_wal(c):
    deadline = time.monotonic() + 20
    while True:
        try:
            c.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            remaining = deadline - time.monotonic()
            if code is None or (code & 0xff) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or remaining <= 0:
                raise
            time.sleep(min(0.05, remaining))

def initialize():
    with connect() as c:
        _enable_wal(c)
        c.execute("BEGIN IMMEDIATE")
        try:
            _execute_script(c, (ROOT / "backend/migrations/001_initial.sql").read_text(encoding="utf-8"))
            for path in sorted((ROOT / "backend/migrations").glob("*.sql")):
                version = int(path.name.split('_')[0])
                if not c.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
                    _execute_script(c, path.read_text(encoding="utf-8"))
            for key, value in ROLES.items():
                c.execute("INSERT INTO agents VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (key, pack(value)))
            c.commit()
        except Exception:
            c.rollback()
            raise

def event(c, kind, message, task_id=None):
    c.execute("INSERT INTO events(created,kind,message,task_id) VALUES(?,?,?,?)", (now(), kind, message, task_id))

def rows(c, sql, args=()):
    return [dict(row) for row in c.execute(sql, args)]

