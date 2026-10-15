from typing import Any

from catnanny.services.event_service import log_health_event
from catnanny.domain.schemas import ConversationRequest
from catnanny.services.conversation_service import process_turn


def handle_conversation(text: str, request_id: str, session_attributes: dict | None=None) -> dict:
    """Shared text-to-core boundary; platform request verification stays outside."""
    attributes=session_attributes or {}
    response=process_turn(ConversationRequest(text=text,request_id=request_id,source="alexa",
        session_id=attributes.get("backend_session_id"),caregiver_id=attributes.get("caregiver_id")))
    return {"speech":response["speech"],"should_end_session":False,
        "session_attributes":{"backend_session_id":response["session_id"],"caregiver_id":response["caregiver_id"]},
        "data":response}


def handle_log_health_event(slots: dict[str, Any]) -> dict[str, Any]:
    """Thin Alexa adapter. ASK SDK handler will call this with parsed slots."""
    event_type = slots.get("event_type") or "vomit"
    details = {
        "content": slots.get("content"),
        "minutes_after_meal": slots.get("minutes_after_meal"),
    }
    details = {key: value for key, value in details.items() if value is not None}

    result = log_health_event(
        event_type=event_type,
        details=details,
        reporter=slots.get("reporter"),
        source="alexa",
    )

    speech = "Logged."
    if result["follow_up"]:
        speech = result["follow_up"]
    elif result["red_flags"]:
        speech = result["red_flags"][0]["message"]

    return {
        "speech": speech,
        "card_title": "Add a Cat Nanny photo",
        "card_text": f"Add a photo for this event: {result['upload_url']}",
        "data": result,
    }
