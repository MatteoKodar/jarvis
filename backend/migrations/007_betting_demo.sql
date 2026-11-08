-- Eget syntetiskt kapital per omgång. Befintlig budget och Oddslabb lämnas orörda.
CREATE TABLE betting_demo_sessions (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK(state IN ('created','analyzed','no_bets','approved','declined','simulated','settled')),
    frozen TEXT NOT NULL,
    frozen_hash TEXT NOT NULL,
    analysis TEXT,
    decision TEXT CHECK(decision IN ('approved','declined')),
    decision_version INTEGER,
    decision_hash TEXT,
    decision_at TEXT,
    summary TEXT NOT NULL,
    settlement TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE betting_demo_costs (
    session_id TEXT NOT NULL REFERENCES betting_demo_sessions(id),
    event_id TEXT NOT NULL,
    cost_kind TEXT NOT NULL,
    amount_ore INTEGER NOT NULL CHECK(amount_ore >= 0),
    simulated_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY(session_id,event_id,cost_kind)
);
CREATE TABLE betting_demo_bets (
    session_id TEXT NOT NULL REFERENCES betting_demo_sessions(id),
    event_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('home','draw','away')),
    paper_odds INTEGER NOT NULL CHECK(paper_odds >= 10001),
    stake_ore INTEGER NOT NULL CHECK(stake_ore > 0),
    proposal_version INTEGER NOT NULL,
    proposal_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('open','won','lost','void')),
    return_ore INTEGER,
    profit_ore INTEGER,
    result TEXT,
    placed_at TEXT NOT NULL,
    settled_at TEXT,
    PRIMARY KEY(session_id,event_id),
    CHECK((state='open' AND return_ore IS NULL AND profit_ore IS NULL AND result IS NULL AND settled_at IS NULL)
       OR (state!='open' AND return_ore IS NOT NULL AND profit_ore IS NOT NULL AND result IS NOT NULL AND settled_at IS NOT NULL))
);
CREATE TABLE betting_demo_actions (
    action_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES betting_demo_sessions(id),
    operation TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE betting_demo_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES betting_demo_sessions(id),
    operation TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    UNIQUE(session_id,operation)
);
CREATE INDEX betting_demo_recent ON betting_demo_sessions(created_at DESC,id DESC);
INSERT INTO schema_migrations(version) VALUES(7);
