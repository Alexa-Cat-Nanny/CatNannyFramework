import sqlite3
from pathlib import Path

from catnanny.config import DATA_DIR, DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cats (
                household_id TEXT NOT NULL,
                cat_id TEXT NOT NULL,
                name TEXT NOT NULL,
                sex TEXT,
                neutered INTEGER,
                birth_year INTEGER,
                current_food TEXT,
                conditions TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY (household_id, cat_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL,
                cat_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                details TEXT NOT NULL,
                reporter TEXT,
                source TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS photos (
                photo_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                household_id TEXT NOT NULL,
                cat_id TEXT NOT NULL,
                url TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            """
        )
        migration = Path(__file__).parent / "migrations" / "001_core_framework.sql"
        conn.executescript(migration.read_text(encoding="utf-8"))
        conn.executescript((migration.parent / "002_caregivers.sql").read_text(encoding="utf-8"))
        conn.executescript((migration.parent / "003_event_reassignments.sql").read_text(encoding="utf-8"))
