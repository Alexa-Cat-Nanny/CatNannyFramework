from typing import Literal
from pydantic import BaseModel,ConfigDict


class LanguageAction(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    action: Literal["none","correct_cat","add_cat","set_caregiver","select_cat","request_report","show_care_log","new_observation","photo_link","show_record"]
    target_name: str | None
    report_days: int | None
    evidence: str
