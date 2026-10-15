import json
from datetime import datetime, timezone

from catnanny.config import DEFAULT_CAT_ID, DEFAULT_CAT_NAME, DEFAULT_HOUSEHOLD_ID
from catnanny.domain.models import Cat, Event, EventType, Photo
from catnanny.storage.database import get_connection


def ensure_demo_cat() -> Cat:
    cat = get_cat(DEFAULT_HOUSEHOLD_ID, DEFAULT_CAT_ID)
    if cat:
        return cat

    cat = Cat(
        household_id=DEFAULT_HOUSEHOLD_ID,
        cat_id=DEFAULT_CAT_ID,
        name=DEFAULT_CAT_NAME,
        sex="female",
        neutered=True,
        birth_year=2019,
        current_food="demo dry food",
    )
    save_cat(cat)
    return cat


def save_cat(cat: Cat) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO cats (
                household_id, cat_id, name, sex, neutered, birth_year, current_food, conditions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cat.household_id,
                cat.cat_id,
                cat.name,
                cat.sex,
                None if cat.neutered is None else int(cat.neutered),
                cat.birth_year,
                cat.current_food,
                json.dumps(cat.conditions),
            ),
        )


def get_cat(household_id: str, cat_id: str) -> Cat | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cats WHERE household_id = ? AND cat_id = ?",
            (household_id, cat_id),
        ).fetchone()

    if not row:
        return None

    return Cat(
        household_id=row["household_id"],
        cat_id=row["cat_id"],
        name=row["name"],
        sex=row["sex"],
        neutered=None if row["neutered"] is None else bool(row["neutered"]),
        birth_year=row["birth_year"],
        current_food=row["current_food"],
        conditions=json.loads(row["conditions"]),
    )


def save_event(event: Event) -> Event:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (
                event_id, household_id, cat_id, ts, type, details, reporter, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.household_id,
                event.cat_id,
                event.ts.isoformat(),
                event.type.value,
                json.dumps(event.details),
                event.reporter,
                event.source,
            ),
        )
    return event


def get_event(event_id: str) -> Event | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()

    if not row:
        return None

    return _row_to_event(row)


def list_events(household_id: str, cat_id: str, limit: int = 50) -> list[Event]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE household_id = ? AND cat_id = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (household_id, cat_id, limit),
        ).fetchall()

    return [_row_to_event(row) for row in rows]


def save_photo(photo: Photo) -> Photo:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO photos (photo_id, event_id, household_id, cat_id, url, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                photo.photo_id,
                photo.event_id,
                photo.household_id,
                photo.cat_id,
                photo.url,
                photo.uploaded_at.isoformat(),
            ),
        )
    return photo


def list_event_photos(event_id: str) -> list[Photo]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM photos WHERE event_id = ? ORDER BY uploaded_at ASC",
            (event_id,),
        ).fetchall()

    return [
        Photo(
            photo_id=row["photo_id"],
            event_id=row["event_id"],
            household_id=row["household_id"],
            cat_id=row["cat_id"],
            url=row["url"],
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        )
        for row in rows
    ]


def _row_to_event(row) -> Event:
    return Event(
        event_id=row["event_id"],
        household_id=row["household_id"],
        cat_id=row["cat_id"],
        ts=datetime.fromisoformat(row["ts"]),
        type=EventType(row["type"]),
        details=json.loads(row["details"]),
        reporter=row["reporter"],
        source=row["source"],
    )
