"""Back up existing SQLite data, then add core tables without deleting data."""
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catnanny.config import DATABASE_PATH
from catnanny.storage.database import init_db


def counts(conn):
    return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in ("cats", "events", "photos")}


def main():
    before = None
    if DATABASE_PATH.exists():
        directory = DATABASE_PATH.parent / "backups"
        directory.mkdir(exist_ok=True)
        backup = directory / f"before-core-{uuid4().hex}.sqlite3"
        with sqlite3.connect(DATABASE_PATH) as source:
            with sqlite3.connect(backup) as destination:
                source.backup(destination)
            before = counts(source)
        print(f"Backup: {backup}")
    init_db()
    with sqlite3.connect(DATABASE_PATH) as conn:
        after = counts(conn)
        if before is not None:
            assert before == after, "Existing data count changed"
        print(f"Preserved: {after}")
        print("Tables:", [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")])


if __name__ == "__main__":
    main()
