CREATE TABLE dispatch_control (
    id INTEGER PRIMARY KEY CHECK(id=1),
    epoch INTEGER NOT NULL DEFAULT 0
);
INSERT INTO dispatch_control(id,epoch) VALUES(1,0);
-- NULL deliberately blocks continuation of runs created by older code.
ALTER TABLE runs ADD COLUMN dispatch_epoch INTEGER;
CREATE TABLE operations (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    kind TEXT NOT NULL CHECK(kind IN ('model.responses','research.wikipedia')),
    slot TEXT NOT NULL,
    version TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    input_hash TEXT NOT NULL,
    frozen TEXT NOT NULL,
    payload_hash TEXT,
    transport_hash TEXT,
    reservation_id TEXT UNIQUE REFERENCES reservations(id),
    state TEXT NOT NULL CHECK(state IN ('prepared','possible_send','completed','unknown','cancelled')),
    created TEXT NOT NULL,
    authorized TEXT,
    finished TEXT,
    uncertainty TEXT,
    result TEXT,
    UNIQUE(task_id,run_id,slot)
);
CREATE INDEX operations_run ON operations(run_id,state);
INSERT INTO schema_migrations(version) VALUES(4);
