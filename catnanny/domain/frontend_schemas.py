from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel
from catnanny.domain.schemas import ConversationResponse


class PhotoView(BaseModel):
    photo_id: str
    url: str
    uploaded_at: datetime


class EventView(BaseModel):
    event_id: str
    cat_id: str
    cat_name: str
    reporter: str | None = None
    event_type: str
    occurred_at: datetime
    details: dict[str, Any]
    source: str
    status: Literal["awaiting_answer", "completed", "legacy"]
    unknown_fields: list[str]
    photos: list[PhotoView]


class EventPage(BaseModel):
    items: list[EventView]
    total: int
    limit: int
    offset: int


class MessageView(BaseModel):
    request_id: str
    text: str
    submitted_details: dict[str, Any]
    recorded_at: datetime
    response: ConversationResponse


class MessagePage(BaseModel):
    items: list[MessageView]
    total: int
    limit: int
    offset: int


class Capabilities(BaseModel):
    schema_version: str = "1.3"
    extraction_provider: Literal["rules", "openai"]
    ai_configured: bool
    event_types: list[str]
    photo_upload: bool = True
    document_upload: bool = False
    notifications: bool = False
    report_formats: list[str] = ["json"]
    default_language: str = "en"
    default_report_days: int = 7
    multiple_cats: bool = True
    caregiver_attribution: bool = True
    language_management: bool = True
    subject_corrections: bool = True


class ReportItem(BaseModel):
    event_id: str
    time: datetime
    type: str
    details: dict[str, Any]
    photos: list[str]
    status: str
    unknown_fields: list[str]
    reporter: str | None = None


class VetSummary(BaseModel):
    title: str
    cat: str
    cat_id: str
    counts: dict[str, int]
    timeline: list[ReportItem]
    safety_note: str
    start: datetime
    end: datetime


class EventTypeView(BaseModel):
    event_type: str
    details_schema: dict[str, Any]
    questions: list[dict[str, str]]
