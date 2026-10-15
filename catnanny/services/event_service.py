from datetime import datetime, timezone
from typing import Any

from catnanny.config import PUBLIC_BASE_URL
from catnanny.domain.models import Event, EventType
from catnanny.domain.rules import analyze_event
from catnanny.storage.repositories import ensure_demo_cat, list_events, save_event


def log_health_event(
    event_type: str,
    details: dict[str, Any] | None = None,
    reporter: str | None = None,
    source: str = "api",
) -> dict[str, Any]:
    cat = ensure_demo_cat()
    recent_events = list_events(cat.household_id, cat.cat_id, limit=50)
    event = Event(
        household_id=cat.household_id,
        cat_id=cat.cat_id,
        ts=datetime.now(timezone.utc),
        type=EventType(event_type),
        details=details or {},
        reporter=reporter,
        source=source,
    )

    rule_result = analyze_event(cat, event, recent_events)
    save_event(event)

    return {
        "event_id": event.event_id,
        "cat": cat.name,
        "type": event.type.value,
        "details": event.details,
        "follow_up": rule_result.follow_up,
        "red_flags": [flag.model_dump() for flag in rule_result.red_flags],
        "pattern_note": rule_result.pattern_note,
        "upload_url": f"{PUBLIC_BASE_URL}/photos/upload?event_id={event.event_id}",
    }
