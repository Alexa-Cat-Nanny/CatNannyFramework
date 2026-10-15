"""Persistent conversation orchestration shared by API, Alexa and MCP adapters."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from catnanny.config import PUBLIC_BASE_URL, DEFAULT_CAT_ID
from catnanny.domain.models import Event, EventType
from catnanny.domain.questionnaire import missing_fields, next_question
from catnanny.domain.rules import analyze_event
from catnanny.domain.schemas import ConversationRequest, ConversationResponse, DETAIL_MODELS
from catnanny.services.ai_extraction_service import extract_turn
from catnanny.storage.database import get_connection
from catnanny.storage.repositories import _row_to_event
from catnanny.services.profile_service import owned_cat, caregiver, DEFAULT_CAREGIVER_ID, mentioned_cats, cats, unfamiliar_subject
from catnanny.services.language_action_service import handle_language_action


class ConversationNotFound(ValueError):
    pass


class ConversationConflict(ValueError):
    pass


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _snapshot(conn, request):
    receipt = conn.execute("SELECT payload,response FROM conversation_turns WHERE request_id=?", (request.request_id,)).fetchone()
    if receipt:
        if receipt["payload"] != _encode(request.model_dump(mode="json")):
            raise ConversationConflict("request_id already used for different input")
        return None, None, [], json.loads(receipt["response"])
    row = conn.execute("SELECT state FROM conversation_sessions WHERE session_id=?", (request.session_id,)).fetchone() if request.session_id else None
    if request.session_id and row is None:
        raise ConversationNotFound("Session not found")
    state = json.loads(row["state"]) if row else {
        "event_id": None, "event_type": None, "details": {}, "unknown_fields": [],
        "pending_field": None, "occurred_at": None, "cat_id": None,
    }
    rows = conn.execute("SELECT payload,response FROM conversation_turns WHERE session_id=? ORDER BY turn_id DESC LIMIT 6",
                        (request.session_id,)).fetchall() if request.session_id else []
    history = [{"user": json.loads(item["payload"])["text"],
                "question": json.loads(item["response"])["follow_up"]} for item in reversed(rows)]
    return state, row["state"] if row else None, history, None


def get_conversation(session_id, cat_id=None):
    with get_connection() as conn:
        row = conn.execute("SELECT state FROM conversation_sessions WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        raise ConversationNotFound("Session not found")
    state = json.loads(row["state"])
    if cat_id and state.get("cat_id",DEFAULT_CAT_ID) != cat_id:
        raise ConversationNotFound("Conversation not found for this cat")
    response=dict(state["last_response"])
    response.setdefault("cat_id",state.get("cat_id",DEFAULT_CAT_ID))
    if response["cat_id"]:
        response.setdefault("cat_name",owned_cat(response["cat_id"]).name)
    return response


def _save_turn(conn, state, response, session_id, request, now):
    state["last_response"]=response
    conn.execute("""INSERT INTO conversation_sessions VALUES (?,?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at""",
        (session_id,_encode(state),now.isoformat(),now.isoformat()))
    conn.execute("INSERT INTO conversation_turns(request_id,session_id,payload,response,recorded_at) VALUES (?,?,?,?,?)",
        (request.request_id,session_id,_encode(request.model_dump(mode="json")),_encode(response),now.isoformat()))


def process_turn(request: ConversationRequest) -> dict:
    if not request.text.strip() and not request.details and not request.event_type:
        raise ValueError("Provide text, event_type or details")
    now = datetime.now(timezone.utc)
    # Read context first, then call the remote service without holding a SQLite
    # write lock. Recheck state after inference to avoid applying stale patches.
    with get_connection() as conn:
        state, original_state, history, cached = _snapshot(conn, request)
    if cached is not None:
        return cached
    action_response=handle_language_action(request,state,original_state,now)
    if action_response is not None:
        return action_response
    person = caregiver(request.caregiver_id or state.get("active_caregiver_id") or DEFAULT_CAREGIVER_ID)
    matches = mentioned_cats(request.text)
    unfamiliar = unfamiliar_subject(request.text)
    prior_cat = state.get("cat_id",DEFAULT_CAT_ID)
    subject_id = matches[0]["cat_id"] if len(matches)==1 else request.cat_id or prior_cat
    if len(matches)>1 or not subject_id or unfamiliar:
        question = "Which cat is this about? Please name one cat: " + ", ".join(item["name"] for item in cats()) + ". You can also add a cat profile."
        if unfamiliar:
            question=f"I do not have a profile for {unfamiliar}. You can say 'Add a cat named {unfamiliar}', or confirm an existing cat."
        with get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            _,current_state,_,cached=_snapshot(conn,request)
            if cached is not None:
                return cached
            if current_state != original_state:
                raise ConversationConflict("Session changed; reload and retry")
            session_id=request.session_id or f"sess_{uuid4().hex}"
            if (not prior_cat or unfamiliar) and not state.get("pending_text"):
                state["pending_text"]=request.text
                state["pending_occurred_at"]=(request.occurred_at or now).isoformat()
                state["pending_details"]=request.details
                state["pending_event_type"]=request.event_type
                state["pending_reporter"]=person["name"]
            response=ConversationResponse(session_id=session_id,event_id=state["event_id"],status="awaiting_cat",
                event_type=state["event_type"],details=state["details"],unknown_fields=state["unknown_fields"],
                missing_fields=["cat_id"],follow_up=question,red_flags=[],speech=question,occurred_at=state["occurred_at"],
                cat_id=None,cat_name=None,caregiver_id=person["caregiver_id"],caregiver_name=person["name"],extraction_provider="structured").model_dump(mode="json")
            _save_turn(conn,state,response,session_id,request,now)
            return response
    switch_cat=bool(request.session_id and prior_cat and subject_id != prior_cat and len(matches)==1)
    if request.session_id and prior_cat and subject_id != prior_cat and not switch_cat:
        raise ConversationConflict("This conversation belongs to a different cat")
    if switch_cat:
        pending={key:value for key,value in state.items() if key.startswith("pending_") and key!="pending_field"}
        state={"event_id":None,"event_type":None,"details":{},"unknown_fields":[],"pending_field":None,"occurred_at":None,"cat_id":subject_id,**pending}
        history=[]
    cat=owned_cat(subject_id)
    effective_request=request
    if state.get("pending_text"):
        effective_request=request.model_copy(update={
            "text": (state["pending_text"]+"\n"+request.text)[-4000:],
            "details": {**state.get("pending_details",{}),**request.details},
            "event_type":request.event_type or state.get("pending_event_type"),
            "occurred_at":request.occurred_at or datetime.fromisoformat(state["pending_occurred_at"])})
    known_type = effective_request.event_type or state["event_type"]
    if effective_request.details:
        if known_type is None:
            raise ValueError("Clarify event_type before submitting details")
        DETAIL_MODELS[known_type].model_validate(effective_request.details)
    detected, extracted, skipped_fields, provider, clarification = extract_turn(effective_request, state, history)
    if clarification and effective_request.details:
        # Explicit form edits remain authoritative even if accompanying prose
        # cannot be interpreted; the caller's fields were already validated.
        clarification = None
    # One write transaction covers state, event and request receipt. Concurrent
    # retries cannot create two events or overwrite a newer conversation turn.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _, current_state, _, cached = _snapshot(conn, request)
        if cached is not None:
            return cached
        if current_state != original_state:
            raise ConversationConflict("Session changed during extraction; reload the session and retry")
        session_id = (None if switch_cat else request.session_id) or f"sess_{uuid4().hex}"
        if state["event_type"] and detected and detected != state["event_type"]:
            raise ConversationConflict("A different event needs a new session")
        event_type = state["event_type"] or detected
        if request.details and event_type is None:
            raise ValueError("Clarify event_type before submitting details")
        event_saved = False
        if clarification:
            response = ConversationResponse(session_id=session_id, event_id=state["event_id"],
                status="awaiting_answer", event_type=state["event_type"], details=state["details"],
                unknown_fields=state["unknown_fields"], missing_fields=(
                    missing_fields(state["event_type"], state["details"], state["unknown_fields"])
                    if state["event_type"] else ["event_type"]),
                follow_up=clarification, red_flags=state.get("last_response", {}).get("red_flags", []),
                speech=clarification, occurred_at=state["occurred_at"], extraction_provider=provider,
                upload_url=state.get("last_response", {}).get("upload_url")).model_dump(mode="json")
        elif event_type:
            updates = {**extracted, **effective_request.details}
            details = DETAIL_MODELS[event_type].model_validate({**state["details"], **updates}).model_dump()
            unknown = set(state["unknown_fields"])
            for skipped in skipped_fields:
                details[skipped] = None
                unknown.add(skipped)
            for key, value in updates.items():
                if value is not None:
                    unknown.discard(key)
                else:
                    unknown.add(key)
            # Reuse original observation time unless the user explicitly corrects it.
            occurred_at = effective_request.occurred_at or (
                datetime.fromisoformat(state["occurred_at"]) if state["occurred_at"] else now)
            occurred_at = occurred_at.astimezone(timezone.utc)
            event_id = state["event_id"] or f"evt_{uuid4().hex}"
            event = Event(event_id=event_id, household_id=cat.household_id, cat_id=cat.cat_id,
                          ts=occurred_at, type=EventType(event_type), details=details, source=request.source)
            recent = [_row_to_event(item) for item in conn.execute(
                "SELECT * FROM events WHERE household_id=? AND cat_id=? AND event_id<>? AND ts>=? AND ts<=?",
                (cat.household_id, cat.cat_id, event_id,
                 (occurred_at - timedelta(hours=24)).isoformat(), occurred_at.isoformat()))]
            rule_result = analyze_event(cat, event, recent)
            pending, question = next_question(event_type, details, unknown)
            status = "awaiting_answer" if pending else "completed"
            # Existing event source is preserved on follow-up turns.
            conn.execute("""INSERT INTO events (event_id,household_id,cat_id,ts,type,details,reporter,source)
                VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET ts=excluded.ts,details=excluded.details""",
                (event_id, cat.household_id, cat.cat_id, occurred_at.isoformat(), event_type, _encode(details), state.get("pending_reporter",person["name"]), request.source))
            state.update(event_id=event_id, event_type=event_type, details=details,
                         unknown_fields=sorted(unknown), pending_field=pending, occurred_at=occurred_at.isoformat())
            flags = [flag.model_dump() for flag in rule_result.red_flags]
            speech = " ".join([flag["message"] for flag in flags] + ([question] if question else [f"Saved this observation for {cat.name}."]))
            response = ConversationResponse(session_id=session_id, event_id=event_id,
                status=status, event_type=event_type, details=details, unknown_fields=sorted(unknown),
                missing_fields=missing_fields(event_type, details, unknown), follow_up=question,
                red_flags=flags, speech=speech, occurred_at=occurred_at, extraction_provider=provider,
                upload_url=f"{PUBLIC_BASE_URL}/photos/upload?event_id={event_id}").model_dump(mode="json")
            event_saved = True
        else:
            response = ConversationResponse(session_id=session_id, event_id=None, status="awaiting_answer",
                event_type=None, details={}, unknown_fields=[], missing_fields=["event_type"],
                follow_up="Are you recording vomiting or a change in appetite? Please record one observation at a time.", red_flags=[],
                speech="Are you recording vomiting or a change in appetite? Please record one observation at a time.", occurred_at=None,
                extraction_provider=provider).model_dump(mode="json")
        response.update(cat_id=cat.cat_id,cat_name=cat.name,caregiver_id=person["caregiver_id"],caregiver_name=person["name"])
        state["cat_id"] = cat.cat_id
        state["active_caregiver_id"]=person["caregiver_id"]
        for key in ["pending_text","pending_occurred_at","pending_details","pending_event_type","pending_reporter"]:
            state.pop(key,None)
        _save_turn(conn,state,response,session_id,request,now)
        if event_saved:
            conn.execute("""INSERT INTO event_progress VALUES (?,?,?,?,?,?) ON CONFLICT(event_id)
                DO UPDATE SET status=excluded.status,unknown_fields=excluded.unknown_fields,updated_at=excluded.updated_at""",
                (state["event_id"], session_id, response["status"], _encode(state["unknown_fields"]), now.isoformat(), now.isoformat()))
        return response
