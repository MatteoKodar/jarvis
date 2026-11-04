CREATE TABLE IF NOT EXISTS schedule(id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL, at TEXT NOT NULL, goal TEXT NOT NULL, cap INTEGER NOT NULL, remaining INTEGER NOT NULL, version INTEGER NOT NULL, last_day TEXT NOT NULL, expires TEXT NOT NULL);
INSERT OR IGNORE INTO schedule VALUES(1,0,'09:00','Undersök problem och jämför alternativ',500,0,1,'','');
INSERT OR IGNORE INTO schema_migrations VALUES(2);
