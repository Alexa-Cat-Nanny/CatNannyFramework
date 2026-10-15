from datetime import datetime, timedelta, timezone
from catnanny.config import DEFAULT_CAT_ID
from catnanny.services.profile_service import owned_cat
from catnanny.services.query_service import event_page


def build_vet_summary(start=None, end=None, cat_id=DEFAULT_CAT_ID) -> dict:
    cat=owned_cat(cat_id)
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if start >= end:
        raise ValueError("start must be earlier than end")
    # One read snapshot includes every event in the date range, regardless of count.
    events = event_page(None, 0, start, end, cat_id)["items"]
    timeline = []
    for event in events:
        timeline.append(
            {
                "event_id": event["event_id"],
                "time": event["occurred_at"],
                "type": event["event_type"],
                "details": event["details"],
                "photos": [photo["url"] for photo in event["photos"]],
                "status": event["status"],
                "unknown_fields": event["unknown_fields"],
                "reporter":event["reporter"],
            }
        )

    vomit_count = sum(1 for event in events if event["event_type"] == "vomit")
    appetite_count = sum(1 for event in events if event["event_type"] == "appetite")

    return {
        "title": "Cat Nanny Vet Summary",
        "cat": cat.name,
        "cat_id":cat.cat_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "counts": {
            "vomit": vomit_count,
            "appetite": appetite_count,
            "total_events": len(events),
        },
        "timeline": timeline,
        "safety_note": "Cat Nanny describes observations and does not diagnose. Contact a veterinarian for medical advice.",
    }
