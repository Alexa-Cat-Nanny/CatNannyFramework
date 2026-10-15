CREATE TABLE IF NOT EXISTS event_reassignments (
    reassignment_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    from_cat_id TEXT NOT NULL,
    to_cat_id TEXT NOT NULL,
    caregiver_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    corrected_at TEXT NOT NULL
);
