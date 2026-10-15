from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from catnanny.domain.extraction import ExtractionError
from catnanny.services.profile_service import ProfileNotFound

from catnanny.domain.schemas import ConversationRequest, ConversationResponse
from catnanny.services.conversation_service import (
    ConversationConflict, ConversationNotFound, get_conversation, process_turn,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/turns", response_model=ConversationResponse)
def conversation_turn(request: ConversationRequest):
    try:
        return process_turn(request)
    except (ConversationNotFound, ProfileNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConversationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=exc.status_code,
                            detail={"code": exc.code, "message": str(exc)}) from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=ConversationResponse)
def conversation_state(session_id: str, cat_id: str | None = None):
    try:
        return get_conversation(session_id, cat_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
