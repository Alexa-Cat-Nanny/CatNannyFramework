"""Version 1 conversation contract. Unknown observations remain None."""
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool


class Details(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class VomitDetails(Details):
    content: Literal["food", "hairball", "liquid", "foam", "other"] | None = None
    has_blood: StrictBool | None = None
    episode_count: int | None = Field(default=None, ge=1, le=1000)
    low_energy: StrictBool | None = None
    minutes_after_meal: float | None = Field(default=None, ge=0)


class AppetiteDetails(Details):
    status: Literal["not_eating", "eating_less", "normal"] | None = None
    hours_since_food: float | None = Field(default=None, ge=0, le=87600)


DETAIL_MODELS = {"vomit": VomitDetails, "appetite": AppetiteDetails}


class ConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    text: str = Field(default="", max_length=4000)
    source: Literal["simulator", "alexa", "mcp", "api"] = "simulator"
    event_type: Literal["vomit", "appetite"] | None = None
    details: dict = Field(default_factory=dict)
    occurred_at: AwareDatetime | None = None
    cat_id: str | None = Field(default=None, min_length=1, max_length=128)
    caregiver_id: str | None = Field(default=None, min_length=1, max_length=128)


class ConversationResponse(BaseModel):
    schema_version: str = "1.3"
    cat_id: str | None = None
    cat_name: str | None = None
    caregiver_id: str | None = None
    caregiver_name: str | None = None
    session_id: str
    event_id: str | None
    status: Literal["awaiting_cat", "awaiting_confirmation", "awaiting_answer", "completed"]
    event_type: str | None
    details: dict
    unknown_fields: list[str]
    missing_fields: list[str]
    follow_up: str | None
    red_flags: list[dict]
    speech: str
    occurred_at: datetime | None
    upload_url: str | None = None
    notification_status: Literal["not_requested"] = "not_requested"
    extraction_provider: Literal["rules", "openai", "structured"] = "rules"
    ui_action: Literal["none","profiles_updated","caregiver_selected","open_report","open_care_log","new_observation","observation_reassigned","open_photo_link","refresh_record"] = "none"
    action_payload: dict = Field(default_factory=dict)
