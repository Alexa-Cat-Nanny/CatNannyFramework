from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    VOMIT = "vomit"
    APPETITE = "appetite"
    LITTER = "litter"
    ENERGY = "energy"
    WEIGHT = "weight"
    MEAL = "meal"
    MEDICATION = "medication"
    FOOD_CHANGE = "food_change"
    VET_VISIT = "vet_visit"


class Cat(BaseModel):
    household_id: str
    cat_id: str
    name: str
    sex: str | None = None
    neutered: bool | None = None
    birth_year: int | None = None
    current_food: str | None = None
    conditions: list[str] = Field(default_factory=list)


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    household_id: str
    cat_id: str
    ts: datetime
    type: EventType
    details: dict[str, Any] = Field(default_factory=dict)
    reporter: str | None = None
    source: str = "voice"


class RedFlag(BaseModel):
    level: str
    code: str
    message: str


class RuleResult(BaseModel):
    follow_up: str | None = None
    red_flags: list[RedFlag] = Field(default_factory=list)
    pattern_note: str | None = None


class Photo(BaseModel):
    photo_id: str = Field(default_factory=lambda: f"photo_{uuid4().hex[:12]}")
    event_id: str
    household_id: str
    cat_id: str
    url: str
    uploaded_at: datetime
