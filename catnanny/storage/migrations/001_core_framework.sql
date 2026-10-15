CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversation_turns (
    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(session_id),
    payload TEXT NOT NULL,
    response TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session
ON conversation_turns(session_id, turn_id);
CREATE TABLE IF NOT EXISTS event_progress (
    event_id TEXT PRIMARY KEY REFERENCES events(event_id),
    session_id TEXT NOT NULL UNIQUE REFERENCES conversation_sessions(session_id),
    status TEXT NOT NULL,
    unknown_fields TEXT NOT NULL DEFAULT '[]',
    recorded_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
