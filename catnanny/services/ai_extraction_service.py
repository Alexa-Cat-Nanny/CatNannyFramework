"""Provider selection and validation independent from conversation persistence."""
import os
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, ValidationError

from catnanny.adapters.openai_responses import extract_with_responses
from catnanny.domain.extraction import ExtractionError
from catnanny.domain.schemas import DETAIL_MODELS
from catnanny.services.extraction_service import detect_type, extract


class AISettings(BaseModel):
    provider: Literal["rules", "openai"] = "rules"
    api_key: SecretStr | None = None
    model: str = ""
    timeout_seconds: float = Field(default=20, ge=1, le=120)


def get_ai_settings():
    try:
        return AISettings(provider=os.getenv("CATNANNY_EXTRACTION_PROVIDER", "rules"),
            api_key=os.getenv("OPENAI_API_KEY") or None,
            model=os.getenv("OPENAI_MODEL", "").strip(),
            timeout_seconds=os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    except ValidationError as exc:
        raise ExtractionError("ai_invalid_config", "AI server configuration is invalid.", 503) from exc


def extract_turn(request, state, history):
    # Fully structured callers do not incur an unnecessary model request.
    if not request.text.strip():
        return request.event_type, {}, [], "structured", None
    settings = get_ai_settings()
    if settings.provider == "rules":
        detected = request.event_type or detect_type(request.text)
        event_type = state["event_type"] or detected
        updates, skipped = extract(request.text, event_type, state["pending_field"]) if event_type else ({}, None)
        return detected, updates, [skipped] if skipped else [], "rules", None
    context = {"event_type": state["event_type"] or request.event_type,
               "details": state["details"], "unknown_fields": state["unknown_fields"],
               "pending_field": state["pending_field"],
               "previous_question": state.get("last_response", {}).get("follow_up"),
               "recent_turns": history}
    result = extract_with_responses(request.text, context, settings)
    if result.intent in {"multiple_events", "unclear"}:
        question = ("Please record one observation at a time. Start a new observation for a separate episode." if result.intent == "multiple_events"
                    else "I could not identify the observation. Please add a little detail or fill in the fields directly.")
        return None, {}, [], "openai", question
    detected = request.event_type or result.event_type
    event_type = detected or state["event_type"]
    if event_type is None and result.updates:
        raise ExtractionError("ai_invalid_output", "AI did not identify an event type for its observations.")
    updates = {}
    for item in result.updates:
        if item.field in updates or not item.evidence.strip() or item.evidence not in request.text:
            raise ExtractionError("ai_invalid_output", "AI observations lack valid source evidence.")
        updates[item.field] = item.value
    if event_type:
        try:
            DETAIL_MODELS[event_type].model_validate(updates)
        except ValidationError as exc:
            raise ExtractionError("ai_invalid_output", "AI observations contain invalid fields or values.") from exc
    return detected, updates, [], "openai", None
