CREATE TABLE odds_lab_runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('synthetic','forward')),
    created TEXT NOT NULL,
    policy TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    head_hash TEXT NOT NULL
);
-- En verklig observationsserie kan inte återställas efter ett dåligt utfall.
CREATE UNIQUE INDEX odds_one_forward ON odds_lab_runs(kind) WHERE kind='forward';
CREATE TABLE odds_lab_records (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES odds_lab_runs(id),
    kind TEXT NOT NULL CHECK(kind IN ('snapshot','result','cost')),
    entity_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    digest TEXT NOT NULL,
    UNIQUE(run_id,kind,entity_id)
);
CREATE TABLE odds_lab_actions (
    action_id TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    response TEXT NOT NULL
);
INSERT INTO schema_migrations(version) VALUES(5);
