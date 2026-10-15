from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from catnanny.domain.models import Event, EventType
from catnanny.storage.repositories import ensure_demo_cat, save_event


def test_frontend_read_endpoints_and_cors(isolated_db):
    from app import app
    with TestClient(app) as client:
        data = client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "front", "text": "猫吐了两次"}).json()
        assert client.get("/capabilities").json()["document_upload"] is False
        assert len(client.get("/event-types").json()) == 2
        page = client.get("/events?limit=1").json()
        assert page["total"] == 1
        assert page["items"][0]["status"] == "awaiting_answer"
        assert client.get(f"/events/{data['event_id']}").json()["details"]["episode_count"] == 2
        messages = client.get(f"/conversations/{data['session_id']}/messages").json()
        assert messages["items"][0]["text"] == "猫吐了两次"
        assert client.get("/events/missing").status_code == 404
        assert client.get("/events?limit=0").status_code == 422
        assert client.get("/conversations/missing/messages").status_code == 404
        preflight = client.options("/conversations/turns", headers={"Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert client.get("/openapi.json").status_code == 200


def test_report_is_date_range_not_thirty_rows(isolated_db):
    from app import app
    cat = ensure_demo_cat()
    now = datetime.now(timezone.utc)
    for index in range(35):
        save_event(Event(household_id=cat.household_id, cat_id=cat.cat_id,
            ts=now-timedelta(hours=index+1), type=EventType.VOMIT))
    save_event(Event(household_id=cat.household_id, cat_id=cat.cat_id,
        ts=now-timedelta(days=31), type=EventType.APPETITE))
    with TestClient(app) as client:
        assert client.get("/reports/vet-summary").json()["counts"]["total_events"] == 35
        params = {"start": (now-timedelta(days=32)).isoformat(), "end": (now-timedelta(days=30)).isoformat()}
        assert client.get("/reports/vet-summary", params=params).json()["counts"]["appetite"] == 1
        assert client.get("/events", params=params).json()["total"] == 1
        assert client.get("/reports/vet-summary", params={"start":now.isoformat(), "end":now.isoformat()}).status_code == 422
