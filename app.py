from typing import Any
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AwareDatetime, BaseModel, Field

from catnanny.config import UPLOAD_DIR, DEFAULT_CAT_ID
from catnanny.services.profile_service import ProfileNotFound
from catnanny.services.event_service import log_health_event
from catnanny.services.photo_service import save_event_photo, PhotoValidationError
from catnanny.services.report_service import build_vet_summary
from catnanny.storage.database import init_db
from catnanny.web.routes_conversations import router as conversation_router
from catnanny.web.routes_frontend import router as frontend_router
from catnanny.domain.frontend_schemas import VetSummary
from catnanny.web.routes_pages import router as pages_router, STATIC_DIR


class LogEventRequest(BaseModel):
    event_type: str = "vomit"
    details: dict[str, Any] = Field(default_factory=dict)
    reporter: str | None = None
    source: str = "api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Cat Nanny", lifespan=lifespan)
app.include_router(conversation_router)
app.include_router(frontend_router)
app.include_router(pages_router)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
app.add_middleware(CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if origin.strip()],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events")
def create_event(payload: LogEventRequest) -> dict[str, Any]:
    return log_health_event(
        event_type=payload.event_type,
        details=payload.details,
        reporter=payload.reporter,
        source=payload.source,
    )


@app.post("/photos/upload")
def upload_photo(event_id: str = Form(...), photo: UploadFile = File(...)) -> dict[str, Any]:
    try:
        saved = save_event_photo(event_id, photo)
    except PhotoValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "photo": saved.model_dump()}


@app.get("/reports/vet-summary", response_model=VetSummary)
def vet_summary(start: AwareDatetime | None = None, end: AwareDatetime | None = None,cat_id: str=DEFAULT_CAT_ID) -> dict[str, Any]:
    try:
        return build_vet_summary(start, end,cat_id)
    except ProfileNotFound as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
