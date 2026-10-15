"""Shared-household local demo profiles. Caregiver selection is attribution, not login."""
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
import re
from catnanny.config import DEFAULT_HOUSEHOLD_ID
from catnanny.domain.models import Cat
from catnanny.storage.database import get_connection
from catnanny.storage.repositories import ensure_demo_cat, get_cat, save_cat

DEFAULT_CAREGIVER_ID = "demo_caregiver"


class ProfileNotFound(ValueError):
    pass


class CatCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    sex: Literal["male", "female"] | None = None
    birth_year: int | None = Field(default=None, ge=1980, le=datetime.now().year)


class CaregiverCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)


def owned_cat(cat_id):
    if cat_id == "mochi":
        ensure_demo_cat()
    cat = get_cat(DEFAULT_HOUSEHOLD_ID, cat_id)
    if cat is None:
        raise ProfileNotFound("Cat profile not found")
    return cat


def cats():
    ensure_demo_cat()
    with get_connection() as conn:
        ids = [row[0] for row in conn.execute("SELECT cat_id FROM cats WHERE household_id=? ORDER BY name,cat_id", (DEFAULT_HOUSEHOLD_ID,))]
    return [owned_cat(cat_id).model_dump(mode="json") for cat_id in ids]


def create_cat(payload: CatCreate):
    if any(cat["name"].casefold() == payload.name.casefold() for cat in cats()):
        raise ValueError("A cat with this name already exists. Use a distinct name for voice matching.")
    cat = Cat(household_id=DEFAULT_HOUSEHOLD_ID, cat_id=f"cat_{uuid4().hex}", **payload.model_dump())
    save_cat(cat)
    return cat.model_dump(mode="json")


def caregivers():
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO caregivers VALUES (?,?,?,?)",
            (DEFAULT_CAREGIVER_ID, DEFAULT_HOUSEHOLD_ID, "Alex", datetime.now(timezone.utc).isoformat()))
        rows=conn.execute("SELECT caregiver_id,name FROM caregivers WHERE household_id=? ORDER BY name,caregiver_id", (DEFAULT_HOUSEHOLD_ID,)).fetchall()
    return [dict(row) for row in rows]


def caregiver(caregiver_id):
    caregivers()
    with get_connection() as conn:
        row = conn.execute("SELECT caregiver_id,name FROM caregivers WHERE household_id=? AND caregiver_id=?", (DEFAULT_HOUSEHOLD_ID,caregiver_id)).fetchone()
    if row is None:
        raise ProfileNotFound("Caregiver not found")
    return dict(row)


def create_caregiver(payload: CaregiverCreate):
    identifier = f"person_{uuid4().hex}"
    with get_connection() as conn:
        conn.execute("INSERT INTO caregivers VALUES (?,?,?,?)", (identifier,DEFAULT_HOUSEHOLD_ID,payload.name,datetime.now(timezone.utc).isoformat()))
    return {"caregiver_id":identifier,"name":payload.name}


def mentioned_cats(text):
    matches=[]
    for cat in cats():
        name=cat["name"]
        pattern=(r"(?<!\w)"+re.escape(name)+r"(?!\w)") if name.isascii() else re.escape(name)
        if re.search(pattern,text,re.I):
            matches.append(cat)
    return matches


def unfamiliar_subject(text):
    """Conservative safeguard for explicit unregistered names, not general NER."""
    match=re.search(r"\b([A-Z][A-Za-z'-]{1,50})\s+(?:vomit(?:ed|ing)?|threw up|is not eating|won't eat)\b",text)
    candidate=match[1] if match else None
    if not candidate:
        introduced=re.search(r"(?:记录(?:一下)?|关于|说的是|讲的是|指的是)\s*([A-Za-z][A-Za-z'-]{1,50})",text)
        candidate=introduced[1] if introduced else None
    if not candidate and re.fullmatch(r"[A-Z][A-Za-z'-]{1,50}",text.strip()):
        possible=text.strip()
        if possible.casefold() not in {"yes","no","food","hairball","liquid","foam","unknown","normal","other","okay","ok","yesterday","today"}:
            candidate=possible
    if candidate in {"He","She","It","My","The","Cat"}:
        return None
    if candidate and not any(cat["name"].casefold()==candidate.casefold() for cat in cats()):
        return candidate
    return None
