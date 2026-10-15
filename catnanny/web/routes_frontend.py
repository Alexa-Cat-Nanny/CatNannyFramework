from fastapi import APIRouter, HTTPException, Query
from pydantic import AwareDatetime
from catnanny.domain.frontend_schemas import Capabilities, EventPage, EventView, MessagePage, EventTypeView
from catnanny.domain.questionnaire import QUESTIONS
from catnanny.domain.schemas import DETAIL_MODELS
from catnanny.domain.extraction import ExtractionError
from catnanny.services.ai_extraction_service import get_ai_settings
from catnanny.services.conversation_service import ConversationNotFound
from catnanny.services.query_service import event_page, event_detail, conversation_messages
from catnanny.config import DEFAULT_CAT_ID
from catnanny.domain.models import Cat
from catnanny.services.profile_service import CatCreate, CaregiverCreate, ProfileNotFound, cats, create_cat, owned_cat, caregivers, create_caregiver

router = APIRouter(tags=["frontend"])


@router.get("/cats", response_model=list[Cat])
def cat_profiles():
    return cats()


@router.post("/cats", response_model=Cat, status_code=201)
def add_cat(payload: CatCreate):
    try:
        return create_cat(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc


@router.get("/cats/{cat_id}", response_model=Cat)
def cat_profile(cat_id: str):
    try:
        return owned_cat(cat_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc


@router.get("/caregivers")
def caregiver_profiles():
    return caregivers()


@router.post("/caregivers",status_code=201)
def add_caregiver(payload: CaregiverCreate):
    return create_caregiver(payload)


@router.get("/capabilities", response_model=Capabilities)
def capabilities():
    try:
        settings = get_ai_settings()
    except ExtractionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    return Capabilities(extraction_provider=settings.provider,
                        ai_configured=bool(settings.api_key and settings.model), event_types=list(DETAIL_MODELS))


@router.get("/event-types", response_model=list[EventTypeView])
def event_types():
    return [{"event_type": name, "details_schema": model.model_json_schema(),
             "questions": [{"field": field, "text": text} for field, text in QUESTIONS[name]]}
            for name, model in DETAIL_MODELS.items()]


@router.get("/events", response_model=EventPage)
def events(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
           start: AwareDatetime | None = None, end: AwareDatetime | None = None,cat_id: str=DEFAULT_CAT_ID):
    if start and end and start >= end:
        raise HTTPException(status_code=422, detail="start must be earlier than end")
    try:
        return event_page(limit, offset, start, end,cat_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc


@router.get("/events/{event_id}", response_model=EventView)
def event(event_id: str,cat_id: str | None=None):
    try:
        return event_detail(event_id,cat_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations/{session_id}/messages", response_model=MessagePage)
def messages(session_id: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),cat_id: str | None=None):
    try:
        return conversation_messages(session_id, limit, offset,cat_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
