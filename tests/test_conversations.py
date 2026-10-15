from uuid import uuid4
import pytest
from pydantic import ValidationError
from catnanny.domain.schemas import ConversationRequest
from catnanny.services.conversation_service import (
    process_turn, get_conversation, ConversationConflict, ConversationNotFound,
)


def turn(text="", session=None, **kwargs):
    return process_turn(ConversationRequest(cat_id="mochi", request_id=uuid4().hex, session_id=session, text=text, **kwargs))


def test_multiturn_updates_one_event_and_persists(isolated_db):
    a = turn("猫今天吐了两次")
    b = turn("食物", a["session_id"])
    c = turn("没有", a["session_id"])
    d = turn("精神正常", a["session_id"])
    assert {r["event_id"] for r in [a, b, c, d]} == {a["event_id"]}
    assert c["details"]["has_blood"] is False
    assert d["status"] == "completed"
    assert get_conversation(a["session_id"]) == d
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0] == 4
        assert conn.execute("SELECT status FROM event_progress").fetchone()[0] == "completed"


def test_retries_are_idempotent_and_conflicting_reuse_is_rejected(isolated_db):
    request = ConversationRequest(cat_id="mochi", request_id="same", text="猫吐了")
    result = process_turn(request)
    assert process_turn(request) == result
    with pytest.raises(ConversationConflict):
        process_turn(request.model_copy(update={"text": "猫不吃饭"}))
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0] == 1


def test_unknown_skip_and_later_correction(isolated_db):
    result = turn("猫吐了")
    session = result["session_id"]
    result = turn("不知道", session)
    assert result["details"]["content"] is None
    assert result["unknown_fields"] == ["content"]
    assert result["missing_fields"][0] == "has_blood"
    result = turn("补充一下，是食物", session)
    assert result["details"]["content"] == "food"
    assert "content" not in result["unknown_fields"]


def test_completed_event_can_be_corrected_and_reopened(isolated_db):
    result = turn(event_type="vomit", details={"content": "food", "has_blood": False,
        "episode_count": 1, "low_energy": False})
    assert result["status"] == "completed"
    corrected = turn("有血", result["session_id"])
    assert corrected["event_id"] == result["event_id"]
    assert corrected["details"]["has_blood"] is True
    assert any(x["code"] == "vomit_blood" for x in corrected["red_flags"])


def test_appetite_context(isolated_db):
    a = turn("猫不吃饭")
    b = turn("12小时", a["session_id"])
    assert b["status"] == "completed"
    assert b["details"] == {"status": "not_eating", "hours_since_food": 12.0}


def test_unrecognized_input_does_not_create_event(isolated_db):
    a = turn("猫打喷嚏")
    assert a["event_id"] is None
    assert a["missing_fields"] == ["event_type"]
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    b = turn("这次记录呕吐", a["session_id"])
    assert b["event_id"]


def test_invalid_updates_roll_back_everything(isolated_db):
    a = turn("猫吐了")
    with pytest.raises(ValidationError):
        turn(session=a["session_id"], details={"episode_count": -2})
    assert get_conversation(a["session_id"]) == a
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0] == 1


def test_missing_session_and_different_category(isolated_db):
    with pytest.raises(ConversationNotFound):
        turn("没有", "missing")
    a = turn("猫吐了")
    with pytest.raises(ConversationConflict):
        turn("猫不吃饭", a["session_id"])


def test_sessions_do_not_share_pending_fields(isolated_db):
    a = turn("猫吐了食物")
    b = turn("猫不吃饭")
    answer = turn("没有", a["session_id"])
    assert answer["details"]["has_blood"] is False
    assert get_conversation(b["session_id"]) == b


def test_repeated_turns_do_not_count_as_repeated_vomiting(isolated_db):
    a = turn("猫吐了食物")
    b = turn("没有", a["session_id"])
    c = turn("两次", a["session_id"])
    assert not any(x["code"] == "vomit_three_times_24h" for x in c["red_flags"])


def test_occurred_at_is_preserved_on_followups(isolated_db):
    a = turn("猫吐了", occurred_at="2026-10-10T12:00:00Z")
    b = turn("食物", a["session_id"])
    assert a["occurred_at"] == b["occurred_at"]


def test_schema_upgrade_keeps_existing_event(isolated_db):
    from catnanny.services.event_service import log_health_event
    original = log_health_event("vomit", {"content": "food"})
    isolated_db.init_db()
    isolated_db.init_db()
    from catnanny.storage.repositories import get_event
    assert get_event(original["event_id"]).details == {"content": "food"}


def test_resume_in_fresh_python_process(isolated_db):
    import json
    import os
    import subprocess
    import sys
    a = turn("猫不吃饭")
    env = dict(os.environ, CATNANNY_DATA_DIR=str(isolated_db.DATA_DIR), PYTHONIOENCODING="utf-8")
    code = (
        "import json; from catnanny.domain.schemas import ConversationRequest; "
        "from catnanny.services.conversation_service import process_turn; "
        "print(json.dumps(process_turn(ConversationRequest(cat_id='mochi', request_id='restart', "
        f"session_id={a['session_id']!r}, details={{'hours_since_food': 12}}))))"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    b = json.loads(result.stdout)
    assert b["event_id"] == a["event_id"]
    assert b["status"] == "completed"


def test_concurrent_retry_creates_one_event(isolated_db):
    from concurrent.futures import ThreadPoolExecutor
    from catnanny.storage.repositories import ensure_demo_cat
    ensure_demo_cat()
    request = ConversationRequest(cat_id="mochi", request_id="parallel", text="猫吐了")
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: process_turn(request), range(3)))
    assert results[0] == results[1] == results[2]
    with isolated_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
