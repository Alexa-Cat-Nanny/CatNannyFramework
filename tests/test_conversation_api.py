from fastapi.testclient import TestClient


def test_http_conversation_and_resume(isolated_db):
    from app import app
    with TestClient(app) as client:
        first = client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "one", "text": "猫不吃饭"})
        assert first.status_code == 200
        session_id = first.json()["session_id"]
        response = client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "two", "session_id": session_id, "text": "12小时"})
        assert response.json()["status"] == "completed"
        assert client.get(f"/conversations/{session_id}").json() == response.json()
        assert client.get("/reports/vet-summary").json()["timeline"][0]["event_id"] == first.json()["event_id"]
        assert client.get("/conversations/missing").status_code == 404
        assert client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "one", "text": "different"}).status_code == 409
        assert client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "bad", "event_type": "vomit", "details": {"has_blood": "false"}}).status_code == 422


def test_legacy_api_still_works(isolated_db):
    from app import app
    with TestClient(app) as client:
        result = client.post("/events", json={"event_type": "vomit", "details": {"content": "food"}})
        assert result.status_code == 200
        assert result.json()["event_id"]
        assert result.json()["upload_url"]
