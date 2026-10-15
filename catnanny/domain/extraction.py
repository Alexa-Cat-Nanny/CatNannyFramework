"""Strict structured-output contract: return patches, never a replacement record."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr

ObservationField = Literal["content", "has_blood", "episode_count", "low_energy",
                           "minutes_after_meal", "status", "hours_since_food"]


class FieldUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: ObservationField
    value: StrictBool | StrictInt | StrictFloat | StrictStr | None
    evidence: str


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    intent: Literal["observation", "correction", "multiple_events", "unclear"]
    event_type: Literal["vomit", "appetite"] | None
    updates: list[FieldUpdate]


class ExtractionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
