import shutil
import sqlite3
import threading
import time
from types import SimpleNamespace

import pytest

from jarvis import db


REAL_CONNECT = sqlite3.connect
MIGRATIONS = db.ROOT / "backend/migrations"
DEMO_TABLES = {
    "betting_demo_sessions", "betting_demo_costs", "betting_demo_bets",
    "betting_demo_actions", "betting_demo_events",
}


def _database(tmp_path, monkeypatch, version=0):
    # The autouse fixture has already initialized its own database. Use another file.
    folder = tmp_path / "initialization-only"
    folder.mkdir()
    path = folder / "demo.sqlite3"
    monkeypatch.setenv("JARVIS_DATA_DIR", str(folder))
    monkeypatch.setenv("JARVIS_MODE", "DEMO")
    if version:
        with REAL_CONNECT(path) as c:
            for migration in sorted(MIGRATIONS.glob("*.sql")):
                if int(migration.name.split("_")[0]) <= version:
                    c.executescript(migration.read_text(encoding="utf-8"))
            c.execute("UPDATE settings SET state='stopped',total=123456 WHERE id=1")
            c.execute("INSERT INTO messages(role,content,created) VALUES('owner','bevara historik','synthetic')")
            c.execute("INSERT INTO events(created,kind,message) VALUES('synthetic','test_history','bevara')")
            c.execute("INSERT INTO odds_lab_runs VALUES('history','synthetic','synthetic','{}','policy','head')")
    return path


def _history(path):
    with REAL_CONNECT(path) as c:
        return {
            table: c.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in ("settings", "messages", "events", "odds_lab_runs", "odds_lab_records")
        }


def _assert_complete(path):
    with REAL_CONNECT(path) as c:
        assert c.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert c.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("SELECT version,count(*) FROM schema_migrations GROUP BY version ORDER BY version").fetchall() == [
            (version, 1) for version in range(1, 8)
        ]
        # Compare the whole resulting schema with the unchanged migration files.
        with REAL_CONNECT(":memory:") as expected:
            for migration in sorted(MIGRATIONS.glob("*.sql")):
                expected.executescript(migration.read_text(encoding="utf-8"))
            sql = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
            assert c.execute(sql).fetchall() == expected.execute(sql).fetchall()
        assert c.execute("SELECT count(*) FROM agents").fetchone() == (10,)


def _join_workers(workers):
    # Cover WAL retries (20s), an in-flight SQLite wait (2s), and BEGIN (2s).
    deadline = time.monotonic() + 30
    for worker in workers:
        if worker.ident is not None:
            worker.join(max(0, deadline - time.monotonic()))
    alive = [worker.name for worker in workers if worker.is_alive()]
    assert not alive, f"Initialization workers did not terminate: {alive}"


def _parallel_initialize(monkeypatch):
    """Pause A at its real missing-version fetch, then observe B's lock attempt.

    Old code reaches B's bootstrap executescript before its version check.
    Signal there too, and release A immediately: never wait for B to get the
    same exclusive lock as A. The real fetch's transaction flag detects that
    old race even when bootstrap happens to serialize the observed outcome.
    """
    a_checked = threading.Event()
    b_attempting = threading.Event()
    release_a = threading.Event()
    errors = []
    checks = []
    statements = []
    workers = []

    def before(c, sql):
        name = threading.current_thread().name
        normalized = sql.strip().upper()
        statements.append((name, normalized, c.in_transaction))
        if name == "init-B" and (
            normalized.startswith("BEGIN IMMEDIATE")
            or "CREATE TABLE IF NOT EXISTS SCHEMA_MIGRATIONS" in normalized
        ):
            b_attempting.set()

    class ObservedCursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            before(self.connection, sql)
            self.version = parameters[0] if sql.startswith("SELECT 1 FROM schema_migrations WHERE version=?") else None
            return super().execute(sql, parameters)

        def fetchone(self):
            row = super().fetchone()
            if self.version is not None:
                name = threading.current_thread().name
                checks.append((name, self.version, row is not None, self.connection.in_transaction))
                if name == "init-A" and self.version == 7 and row is None:
                    a_checked.set()
                    if not release_a.wait(5):
                        raise AssertionError("A was not released after version 7 check")
            return row

    class ObservedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.strip().upper().startswith("PRAGMA BUSY_TIMEOUT="):
                sql = "PRAGMA busy_timeout=2000"
            return self.cursor(factory=ObservedCursor).execute(sql, parameters)

        def executescript(self, sql):
            # Instrument the old path as well, without replacing real SQLite work.
            before(self, sql)
            return super().executescript(sql)

    def connect(*args, **kwargs):
        kwargs["timeout"] = 2
        kwargs["factory"] = ObservedConnection
        return REAL_CONNECT(*args, **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect)

    def initialize():
        try:
            db.initialize()
        except BaseException as exc:
            errors.append((threading.current_thread().name, exc))

    try:
        a = threading.Thread(target=initialize, name="init-A", daemon=True)
        workers.append(a)
        a.start()
        assert a_checked.wait(5), f"A did not reach the real missing-version check: {errors!r}"
        b = threading.Thread(target=initialize, name="init-B", daemon=True)
        workers.append(b)
        b.start()
        assert b_attempting.wait(5), f"B did not attempt initialization while A was paused: {errors!r}"
    finally:
        release_a.set()
        _join_workers(workers)
    return checks, statements, errors


def test_parallel_upgrade_checks_versions_under_write_lock(tmp_path, monkeypatch):
    """Stable negative-control target: old initialize checks version 7 outside a transaction."""
    path = _database(tmp_path, monkeypatch, version=6)
    with REAL_CONNECT(path) as c:
        assert c.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() == [(v,) for v in range(1, 7)]
        tables = {row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not (tables & DEMO_TABLES)
    history = _history(path)
    checks, statements, errors = _parallel_initialize(monkeypatch)
    assert checks and all(in_transaction for _, _, _, in_transaction in checks), checks
    assert not errors, repr(errors)
    assert [(name, present, active) for name, version, present, active in checks if version == 7] == [
        ("init-A", False, True), ("init-B", True, True),
    ]
    for name, sql, active in statements:
        if not sql.startswith(("PRAGMA ", "BEGIN IMMEDIATE")):
            assert active, (name, sql, active)
    _assert_complete(path)
    assert _history(path) == history
    db.initialize()
    assert _history(path) == history
    _assert_complete(path)


def test_parallel_fresh_database_initialization(tmp_path, monkeypatch):
    path = _database(tmp_path, monkeypatch)
    assert not path.exists()
    # Start together at the actual WAL call to exercise fresh-file contention.
    ready = threading.Barrier(2, timeout=5)
    errors = []
    wal_calls = []

    class FreshConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.strip().upper() == "PRAGMA JOURNAL_MODE=WAL":
                wal_calls.append(self.in_transaction)
                if not getattr(self, "waited", False):
                    self.waited = True
                    ready.wait()
            if sql.strip().upper().startswith("PRAGMA BUSY_TIMEOUT="):
                sql = "PRAGMA busy_timeout=2000"
            return super().execute(sql, parameters)

    def connect(*args, **kwargs):
        kwargs.update(timeout=2, factory=FreshConnection)
        return REAL_CONNECT(*args, **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect)

    def initialize():
        try:
            db.initialize()
        except BaseException as exc:
            errors.append(exc)

    workers = [threading.Thread(target=initialize, daemon=True) for _ in range(2)]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
    finally:
        ready.abort()
        _join_workers(workers)
    assert not errors, repr(errors)
    assert len(wal_calls) >= 2 and not any(wal_calls)
    # The barrier belongs to the two workers, not the sequential restart below.
    monkeypatch.setattr(db.sqlite3, "connect", REAL_CONNECT)
    _assert_complete(path)
    history = _history(path)
    db.initialize()
    assert _history(path) == history


def _extra_migration(tmp_path, monkeypatch, sql):
    root = tmp_path / "migration-source"
    folder = root / "backend/migrations"
    shutil.copytree(MIGRATIONS, folder)
    path = folder / "008_test.sql"
    path.write_text(sql, encoding="utf-8")
    monkeypatch.setattr(db, "ROOT", root)
    return path


def test_migration_statement_boundaries_and_trigger(tmp_path, monkeypatch):
    path = _database(tmp_path, monkeypatch, version=7)
    _extra_migration(tmp_path, monkeypatch, """
-- comment containing ;
/* block ; comment */ CREATE TABLE fragments(value TEXT); CREATE TABLE audit(value TEXT);
CREATE TRIGGER record_fragment AFTER INSERT ON fragments BEGIN
    INSERT INTO audit VALUES('trigger; one'); INSERT INTO audit VALUES(NEW.value);
END;
INSERT INTO fragments VALUES('it''s; intact'); INSERT INTO fragments VALUES('second');
INSERT INTO schema_migrations VALUES(8); -- final comment ;
/* final block ; comment */
""")
    db.initialize()
    with REAL_CONNECT(path) as c:
        assert c.execute("SELECT * FROM fragments").fetchall() == [("it's; intact",), ("second",)]
        assert c.execute("SELECT * FROM audit").fetchall() == [
            ("trigger; one",), ("it's; intact",), ("trigger; one",), ("second",),
        ]
        assert c.execute("SELECT count(*) FROM schema_migrations WHERE version=8").fetchone() == (1,)
    db.initialize()
    with REAL_CONNECT(path) as c:
        assert c.execute("SELECT count(*) FROM audit").fetchone() == (4,)


@pytest.mark.parametrize("failure", ["INSERT INTO table_that_does_not_exist VALUES(1);", "invalid trailing fragment"])
def test_failed_migration_rolls_back_marker_schema_and_replays(tmp_path, monkeypatch, failure):
    path = _database(tmp_path, monkeypatch, version=7)
    history = _history(path)
    prefix = "CREATE TABLE replay(value TEXT); INSERT INTO replay VALUES('synthetic'); INSERT INTO schema_migrations VALUES(8);"
    migration = _extra_migration(tmp_path, monkeypatch, prefix + failure)
    with pytest.raises(sqlite3.OperationalError):
        db.initialize()
    # A new connection must see neither DDL nor data nor the already-written marker.
    with REAL_CONNECT(path) as c:
        assert c.execute("SELECT name FROM sqlite_master WHERE name='replay'").fetchall() == []
        assert c.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() == [(v,) for v in range(1, 8)]
    assert _history(path) == history
    migration.write_text(prefix, encoding="utf-8")
    db.initialize()
    db.initialize()
    with REAL_CONNECT(path) as c:
        assert c.execute("SELECT * FROM replay").fetchall() == [("synthetic",)]
        assert c.execute("SELECT count(*) FROM schema_migrations WHERE version=8").fetchone() == (1,)
    assert _history(path) == history


@pytest.mark.parametrize("code", [None, sqlite3.SQLITE_ERROR, sqlite3.SQLITE_READONLY])
def test_wal_non_lock_error_is_propagated(tmp_path, monkeypatch, code):
    _database(tmp_path, monkeypatch)
    calls = []

    class DeniedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.strip().upper() == "PRAGMA JOURNAL_MODE=WAL":
                calls.append(sql)
                error = sqlite3.OperationalError("synthetic non-lock WAL failure")
                if code is not None:
                    error.sqlite_errorcode = code
                raise error
            return super().execute(sql, parameters)

    def connect(*args, **kwargs):
        kwargs["factory"] = DeniedConnection
        return REAL_CONNECT(*args, **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError, match="synthetic non-lock WAL failure"):
        db.initialize()
    assert len(calls) == 1


@pytest.mark.parametrize("code", [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED])
def test_wal_lock_retry_can_recover(tmp_path, monkeypatch, code):
    path = _database(tmp_path, monkeypatch)
    calls = []

    class BusyOnceConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.strip().upper() == "PRAGMA JOURNAL_MODE=WAL":
                calls.append(self.in_transaction)
                if len(calls) == 1:
                    error = sqlite3.OperationalError("synthetic transient lock")
                    error.sqlite_errorcode = code
                    raise error
            return super().execute(sql, parameters)

    def connect(*args, **kwargs):
        kwargs["factory"] = BusyOnceConnection
        return REAL_CONNECT(*args, **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect)
    db.initialize()
    assert calls == [False, False]
    _assert_complete(path)


def test_wal_lock_retry_stops_at_deadline(tmp_path, monkeypatch):
    _database(tmp_path, monkeypatch)
    calls = []
    moments = iter([0, 1, 21])
    monkeypatch.setattr(db, "time", SimpleNamespace(
        monotonic=lambda: next(moments), sleep=lambda seconds: None,
    ))

    class BusyConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.strip().upper() == "PRAGMA JOURNAL_MODE=WAL":
                calls.append(sql)
                error = sqlite3.OperationalError("synthetic persistent lock")
                error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                raise error
            return super().execute(sql, parameters)

    def connect(*args, **kwargs):
        kwargs["factory"] = BusyConnection
        return REAL_CONNECT(*args, **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError, match="synthetic persistent lock"):
        db.initialize()
    assert len(calls) == 2
