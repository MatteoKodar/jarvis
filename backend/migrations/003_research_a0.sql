CREATE TABLE IF NOT EXISTS research_a0_runs (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL UNIQUE,
    suite_hash TEXT NOT NULL,
    created TEXT NOT NULL,
    payload TEXT NOT NULL,
    digest TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_migrations(version) VALUES(3);
