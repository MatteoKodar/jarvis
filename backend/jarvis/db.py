import json
import sqlite3
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

def initialize():
    with connect() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript((ROOT / "backend/migrations/001_initial.sql").read_text(encoding="utf-8"))
        for path in sorted((ROOT / "backend/migrations").glob("*.sql")):
            version = int(path.name.split('_')[0])
            if not c.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
                c.executescript("BEGIN IMMEDIATE;\n" + path.read_text(encoding="utf-8") + "\nCOMMIT;")
    with connect(True) as c:
        for key, value in ROLES.items():
            c.execute("INSERT INTO agents VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (key, pack(value)))

def event(c, kind, message, task_id=None):
    c.execute("INSERT INTO events(created,kind,message,task_id) VALUES(?,?,?,?)", (now(), kind, message, task_id))

def rows(c, sql, args=()):
    return [dict(row) for row in c.execute(sql, args)]

