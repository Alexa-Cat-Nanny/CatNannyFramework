import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient

from catnanny.adapters import openai_responses
from catnanny.domain.extraction import ExtractionError
from catnanny.domain.schemas import ConversationRequest
from catnanny.services.conversation_service import process_turn, get_conversation, ConversationConflict


@pytest.fixture
def ai_transport(monkeypatch):
    monkeypatch.setenv("CATNANNY_EXTRACTION_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-real")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    calls = []
    responses = []
    client_class = httpx.Client

    def handler(request):
        calls.append(request)
        value = responses.pop(0)
        if callable(value):
            return value(request)
        return httpx.Response(200, json=value)

    monkeypatch.setattr(openai_responses.httpx, "Client",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    return calls, responses


def result(event_type="vomit", updates=None, intent="observation"):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps({"intent": intent, "event_type": event_type,
        "updates": updates or []}, ensure_ascii=False)}]}]}


def turn(text, session_id=None, request_id=None, **kwargs):
    return process_turn(ConversationRequest(cat_id="mochi", text=text, session_id=session_id,
        request_id=request_id or uuid4().hex, **kwargs))


def test_responses_request_context_and_idempotency(isolated_db, ai_transport):
    calls, queue = ai_transport
    queue.append(result(updates=[{"field": "content", "value": "food", "evidence": "猫粮"}]))
    a = turn("吃完吐出来的都是猫粮", request_id="one")
    assert a["details"]["content"] == "food"
    assert a["extraction_provider"] == "openai"
    queue.append(result(updates=[{"field": "has_blood", "value": False, "evidence": "没有"}]))
    b = turn("没有", a["session_id"], "two")
    assert b["details"]["content"] == "food"
    assert b["details"]["has_blood"] is False
    assert b["event_id"] == a["event_id"]
    assert turn("没有", a["session_id"], "two") == b
    assert len(calls) == 2
    body = json.loads(calls[1].content)
    assert str(calls[1].url) == "https://api.openai.com/v1/responses"
    assert body["store"] is False
    assert body["text"]["format"]["strict"] is True
    context = json.loads(body["input"][0]["content"])["context"]
    assert context["pending_field"] == "has_blood"
    assert context["details"]["content"] == "food"
    assert context["recent_turns"][0]["user"] == "吃完吐出来的都是猫粮"


def test_model_unknown_and_correction(isolated_db, ai_transport):
    _, queue = ai_transport
    queue.append(result(updates=[{"field": "episode_count", "value": 2, "evidence": "两次"}]))
    a = turn("吐了两次")
    queue.append(result(updates=[{"field": "content", "value": None, "evidence": "不知道"}]))
    b = turn("不知道", a["session_id"])
    assert b["unknown_fields"] == ["content"]
    queue.append(result(updates=[{"field": "episode_count", "value": 1, "evidence": "一次"}], intent="correction"))
    c = turn("刚才说错了，只有一次", a["session_id"])
    assert c["details"]["episode_count"] == 1
    assert c["details"]["content"] is None


@pytest.mark.parametrize("updates", [
    [{"field": "has_blood", "value": "false", "evidence": "没有"}],
    [{"field": "episode_count", "value": -1, "evidence": "没有"}],
    [{"field": "has_blood", "value": False, "evidence": "invented"}],
    [{"field": "has_blood", "value": False, "evidence": "没有"}]*2,
    [{"field": "status", "value": "not_eating", "evidence": "没有"}],
])
def test_invalid_ai_patch_never_creates_event(isolated_db, ai_transport, updates):
    _, queue = ai_transport
    queue.append(result(updates=updates))
    with pytest.raises(ExtractionError) as error:
        turn("没有")
    assert error.value.code == "ai_invalid_output"
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0] == 0


@pytest.mark.parametrize("intent", ["multiple_events", "unclear"])
def test_ambiguity_clarifies_without_recording_event(isolated_db, ai_transport, intent):
    _, queue = ai_transport
    queue.append(result(event_type=None, intent=intent))
    a = turn("又吐又不吃饭")
    assert a["event_id"] is None
    assert a["status"] == "awaiting_answer"


def test_model_failure_leaves_existing_state_unchanged(isolated_db, ai_transport):
    _, queue = ai_transport
    queue.append(result())
    a = turn("猫吐了")
    queue.append({"status": "incomplete", "output": []})
    with pytest.raises(ExtractionError):
        turn("食物", a["session_id"])
    assert get_conversation(a["session_id"]) == a


@pytest.mark.parametrize("body,code", [
    ({"status": "incomplete", "output": []}, "ai_incomplete"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]}, "ai_refusal"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "not json"}]}]}, "ai_invalid_output"),
])
def test_response_failure_types(isolated_db, ai_transport, body, code):
    _, queue = ai_transport
    queue.append(body)
    with pytest.raises(ExtractionError) as error:
        turn("猫吐了")
    assert error.value.code == code


def test_timeout_retry_and_http_error_redaction(isolated_db, ai_transport):
    from app import app
    _, queue = ai_transport

    def timeout(request):
        raise httpx.ReadTimeout("secret upstream content", request=request)

    queue.append(timeout)
    with TestClient(app) as client:
        response = client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "retry", "text": "猫吐了"})
        assert response.status_code == 504
        assert response.json()["detail"]["code"] == "ai_timeout"
        assert "secret" not in response.text
        queue.append(result())
        assert client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "retry", "text": "猫吐了"}).status_code == 200
        queue.append(lambda request: httpx.Response(429, json={"error": "test-key-never-real"}))
        error = client.post("/conversations/turns", json={"cat_id":"mochi","request_id": "rate", "text": "猫吐了"})
        assert error.status_code == 503
        assert "test-key" not in error.text


def test_missing_key_fails_explicitly_and_structured_input_bypasses_ai(isolated_db, monkeypatch):
    monkeypatch.setenv("CATNANNY_EXTRACTION_PROVIDER", "openai")
    with pytest.raises(ExtractionError) as error:
        turn("猫吐了")
    assert error.value.code == "ai_not_configured"
    response = turn("", event_type="appetite", details={"status": "not_eating"})
    assert response["extraction_provider"] == "structured"


def test_stale_context_is_rejected_and_network_runs_outside_write_lock(isolated_db, ai_transport, monkeypatch):
    calls, queue = ai_transport
    queue.append(result())
    a = turn("猫吐了")

    def concurrent_change(request):
        turn("", a["session_id"], event_type="vomit", details={"content": "food"})
        return httpx.Response(200, json=result(updates=[{"field": "content", "value": "foam", "evidence": "泡沫"}]))

    queue.append(concurrent_change)
    with pytest.raises(ConversationConflict):
        turn("泡沫", a["session_id"])
    assert get_conversation(a["session_id"])["details"]["content"] == "food"


@pytest.mark.parametrize("status,code", [(401,"ai_upstream_error"),(500,"ai_upstream_error"),(429,"ai_rate_limited")])
def test_upstream_errors_are_safe(isolated_db, ai_transport, status, code):
    _, queue = ai_transport
    queue.append(lambda request: httpx.Response(status, text="private upstream body"))
    with pytest.raises(ExtractionError) as error:
        turn("猫吐了")
    assert error.value.code == code
    assert "private" not in str(error.value)


def test_connection_failure_and_invalid_configuration(isolated_db, ai_transport, monkeypatch):
    _, queue = ai_transport
    def disconnected(request):
        raise httpx.ConnectError("private", request=request)
    queue.append(disconnected)
    with pytest.raises(ExtractionError) as error:
        turn("猫吐了")
    assert error.value.code == "ai_connection_error"
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "broken")
    with pytest.raises(ExtractionError) as error:
        turn("猫吐了")
    assert error.value.code == "ai_invalid_config"


def test_explicit_form_edit_survives_unclear_prose(isolated_db, ai_transport):
    _, queue = ai_transport
    a = turn("", event_type="vomit", details={"episode_count":2})
    queue.append(result(event_type=None, intent="unclear"))
    b = turn("补充", a["session_id"], details={"episode_count":1})
    assert b["details"]["episode_count"] == 1


def test_low_cost_model_uses_no_extended_reasoning(isolated_db, ai_transport, monkeypatch):
    calls, queue = ai_transport
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.6-luna")
    queue.append(result())
    turn("猫吐了")
    assert json.loads(calls[0].content)["reasoning"] == {"effort": "none"}


def test_language_model_routes_indirect_subject_correction(isolated_db,ai_transport):
    from catnanny.services.profile_service import create_cat,CatCreate
    calls,queue=ai_transport
    target=create_cat(CatCreate(name='Jeremy'))
    original=turn('',event_type='vomit',details={'content':'food'})
    plan={'action':'correct_cat','target_name':'Jeremy','report_days':None,'evidence':'referring to was Jeremy'}
    queue.append({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(plan)}]}]})
    corrected=turn('I misspoke; the cat I was referring to was Jeremy.',original['session_id'])
    assert corrected['cat_id']==target['cat_id']
    assert corrected['event_id']==original['event_id']
    assert corrected['ui_action']=='observation_reassigned'
    assert json.loads(calls[0].content)['text']['format']['name']=='cat_management_action'
