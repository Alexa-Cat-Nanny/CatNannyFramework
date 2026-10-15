CREATE TABLE IF NOT EXISTS caregivers (
    caregiver_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
