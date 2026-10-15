"""Language equivalents of management controls, with atomic subject corrections."""
import json
import re
from pathlib import Path
from uuid import uuid4

from catnanny.config import DEFAULT_HOUSEHOLD_ID, DEFAULT_CAT_ID, PUBLIC_BASE_URL
from catnanny.domain.models import Cat
from catnanny.domain.schemas import ConversationResponse
from catnanny.domain.language_actions import LanguageAction
from catnanny.domain.extraction import ExtractionError
from catnanny.domain.questionnaire import next_question,missing_fields
from catnanny.domain.rules import analyze_event
from catnanny.services.profile_service import CatCreate, CaregiverCreate, caregiver, DEFAULT_CAREGIVER_ID, cats
from catnanny.storage.database import get_connection
from catnanny.storage.repositories import _row_to_event

PROMPT=(Path(__file__).resolve().parents[1]/"prompts"/"language_actions.txt").read_text(encoding="utf-8")
NAME=r"([A-Za-z][A-Za-z'-]{0,78}|[\u3400-\u9fff]{1,30})"
YES=re.compile(r"^(?:yes(?:[, ]+please)?|yes[, ]+create (?:it|the profile)|confirm|go ahead|是|好的|确认|可以|对)[.!。！\s]*$",re.I)
NO=re.compile(r"^(?:no(?:[, ]+thanks)?|cancel|never mind|取消|不要|不是)[.!。！\s]*$",re.I)


def _plan(action,name=None,days=None,evidence=""):
    return LanguageAction(action=action,target_name=name,report_days=days,evidence=evidence)


def parse_action(text):
    patterns=[r"\bactually\b[\s,]+(?:it|this)(?:\s+(?:is|was)|['’]s)\s+(?:for|about)\s+"+NAME,
              r"\b(?:i\s+meant|it\s+was\s+actually|actually[, ]+(?:it\s+was|this\s+was\s+about)|correct\s+(?:the\s+)?cat\s+to)\s+"+NAME,
              r"\bnot\s+"+NAME+r"\s*[,;]?\s*but\s+"+NAME,
              r"(?:实际上|其实|口误|说错)[^。.!]{0,30}?(?:说的是|讲的是|应该是|指的是|是)\s*"+NAME,
              r"不是\s*"+NAME+r"[，,\s]+(?:而)?是\s*"+NAME]
    for pattern in patterns:
        match=re.search(pattern,text,re.I)
        if match:
            name=match.groups()[-1]
            if name.casefold() not in {"one","two","three","food","foam","liquid","hairball","blood","energy","appetite","normal","once","twice","no","yes","for","about","the","a","an","not"}:
                return _plan("correct_cat",name,evidence=match[0])
    for action,patterns in [
        ("add_cat",[r"\b(?:add|create|register)\s+(?:a\s+|another\s+)?(?:cat|companion)(?:\s+profile)?(?:\s+(?:named|called|for))?\s+"+NAME,r"(?:添加|新增|建立)(?:一只)?(?:猫|宠物)(?:档案)?[：:\s]*"+NAME]),
        ("set_caregiver",[r"\b(?:i am|i'm)\s+"+NAME,r"\b(?:add|select|switch to)\s+(?:a\s+)?caregiver(?:\s+(?:named|called))?\s+"+NAME,r"(?:我是|照护者是|照顾者是|添加照护者)\s*"+NAME]),
        ("select_cat",[r"\b(?:switch to|select)\s+(?:(?:the\s+)?(?:cat|profile)(?:\s+for)?\s+)?"+NAME,r"\bopen\s+(?:the\s+)?(?:profile|companion)(?:\s+for)?\s+"+NAME,r"(?:切换到|选择)(?:猫咪)?\s*"+NAME])]:
        for pattern in patterns:
            match=re.search(pattern,text,re.I)
            if match:
                if action=="set_caregiver" and match[1].casefold() in {"talking","recording","trying","not","unsure","worried","concerned","caring","with","going","looking","about","a","an"}:
                    continue
                return _plan(action,match[1],evidence=match[0])
    if re.search(r"\b(?:show|view|get|send|request|generate|export|download|see)\b.{0,80}\breport\b|(?:查看|生成|导出|发给我).{0,20}(?:报告)",text,re.I):
        days=re.search(r"(?:last\s*)?(\d+)\s*days?|最近\s*(\d+)\s*天",text,re.I)
        names=[c["name"] for c in cats() if re.search(r"(?<!\w)"+re.escape(c["name"])+r"(?!\w)",text,re.I)]
        if len(names)>1:return _plan("request_report",evidence=text)
        return _plan("request_report",names[0] if names else None,int(next(v for v in days.groups() if v)) if days else None,text)
    if re.search(r"\b(?:show|view|open|see)\b.{0,50}\b(?:care log|care history)\b|查看.{0,10}(?:照护记录|历史记录)",text,re.I):
        return _plan("show_care_log",evidence=text)
    if re.search(r"\b(?:start|create|begin)\s+(?:a\s+)?new\s+(?:observation|event)|新建(?:一个)?(?:事件|记录)|开始新记录",text,re.I):
        return _plan("new_observation",evidence=text)
    if re.search(r"\b(?:photo|upload)\s+link\b|照片上传链接|上传照片的链接",text,re.I):
        return _plan("photo_link",evidence=text)
    if re.search(r"\b(?:refresh|show)\s+(?:the\s+)?(?:current\s+)?(?:record|photos)\b|刷新(?:照片|记录)",text,re.I):
        return _plan("show_record",evidence=text)
    return None


def _find_cat(conn,name):
    rows=conn.execute("SELECT * FROM cats WHERE household_id=?",(DEFAULT_HOUSEHOLD_ID,)).fetchall()
    for row in rows:
        if row["name"].casefold()==name.casefold():
            values=dict(row);values["conditions"]=json.loads(values["conditions"])
            return Cat.model_validate(values)
    return None


def _add_cat(conn,name):
    payload=CatCreate(name=name)
    existing=_find_cat(conn,payload.name)
    if existing:return existing
    cat=Cat(household_id=DEFAULT_HOUSEHOLD_ID,cat_id=f"cat_{uuid4().hex}",name=payload.name)
    conn.execute("INSERT INTO cats (household_id,cat_id,name,sex,neutered,birth_year,current_food,conditions) VALUES (?,?,?,?,?,?,?,?)",
        (cat.household_id,cat.cat_id,cat.name,None,None,None,None,"[]"))
    return cat


def _blank(cat_id=None):
    return {"event_id":None,"event_type":None,"details":{},"unknown_fields":[],"pending_field":None,"occurred_at":None,"cat_id":cat_id}


def handle_language_action(request,state,original_state,now):
    # Lazy imports keep persistence helpers shared without an import cycle.
    from catnanny.services.conversation_service import _snapshot,_save_turn,ConversationConflict
    pending=state.get("pending_action")
    approved=False
    cancelled=False
    if pending and YES.fullmatch(request.text.strip()):
        plan=_plan(pending["action"],pending.get("target_name"),pending.get("report_days"),request.text);approved=True
    elif pending and NO.fullmatch(request.text.strip()):
        plan=_plan("none",evidence=request.text);cancelled=True
    elif pending and not pending.get("target_name") and re.fullmatch(NAME,request.text.strip()):
        plan=_plan(pending["action"],request.text.strip(),pending.get("report_days"),request.text)
    else:
        plan=parse_action(request.text)
    provider="structured"
    if plan is None and re.search(r"profile|companion|caregiver|\breport\b|care log|wrong (?:cat|name)|\bmeant\b|misspoke|mistakenly|actually.{0,60}(?:cat|\bfor\b|about|referring|talking|saying)|(?:add|create|register|switch|select).{0,40}\bcat\b|another cat|new cat|口误|讲的是|说的是|说错.{0,8}名字",request.text,re.I):
        from catnanny.services.ai_extraction_service import get_ai_settings
        settings=get_ai_settings()
        if settings.provider=="openai":
            from catnanny.adapters.openai_responses import call_structured_response
            plan=call_structured_response(request.text,{"cat_names":[c["name"] for c in cats()],"current_cat_id":state.get("cat_id"),"has_current_event":bool(state["event_id"])},settings,LanguageAction,PROMPT,"cat_management_action")
            provider="openai"
            if plan.action!="none" and (not plan.evidence.strip() or plan.evidence not in request.text or (plan.target_name and plan.target_name.casefold() not in request.text.casefold())):
                raise ExtractionError("ai_invalid_output","Management action lacks valid source evidence.")
    if plan is None or (plan.action=="none" and not cancelled):
        if not pending:return None
        plan=_plan("none",evidence=request.text)
    person=caregiver(request.caregiver_id or state.get("active_caregiver_id") or DEFAULT_CAREGIVER_ID)
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _,current_state,_,cached=_snapshot(conn,request)
        if cached is not None:return cached
        if current_state!=original_state:raise ConversationConflict("Session changed; reload before applying the action")
        session_id=request.session_id or f"sess_{uuid4().hex}"
        cat_id=state.get("cat_id") or request.cat_id
        cat_row=conn.execute("SELECT name FROM cats WHERE household_id=? AND cat_id=?",(DEFAULT_HOUSEHOLD_ID,cat_id)).fetchone() if cat_id else None
        cat_name=cat_row["name"] if cat_row else None
        speech=""
        ui="none"
        extra={}
        confirm=False
        if cancelled:
            state.pop("pending_action",None);speech="Cancelled. The observation and its cat have not changed."
        elif plan.action=="none":
            speech="Please answer yes or no to the pending confirmation. No records have been moved."
            confirm=True
        elif plan.action=="correct_cat":
            if not state["event_id"]:
                speech="There is no current observation to correct. Please describe the observation and name its cat."
            elif not plan.target_name:
                state["pending_action"]={"action":"correct_cat","target_name":None,"event_id":state["event_id"]}
                speech="Which cat should this current observation belong to?";confirm=True
            else:
                target=_find_cat(conn,plan.target_name)
                if target is None and not approved:
                    # Validate before asking to create a profile; do not infer other details.
                    CatCreate(name=plan.target_name)
                    state["pending_action"]={"action":"correct_cat","target_name":plan.target_name,"event_id":state["event_id"]}
                    speech=f"I do not have a profile for {plan.target_name}. Should I create it and move only this observation, including its photos, from {cat_name} to {plan.target_name}? Please say yes or no."
                    confirm=True
                else:
                    if approved and pending.get("event_id")!=state["event_id"]:
                        raise ConversationConflict("The observation changed since confirmation was requested")
                    target=target or _add_cat(conn,plan.target_name)
                    event_id=state["event_id"]
                    original=conn.execute("SELECT * FROM events WHERE event_id=? AND household_id=?",(event_id,DEFAULT_HOUSEHOLD_ID)).fetchone()
                    if original is None:raise ConversationConflict("Current observation is unavailable")
                    old_cat=original["cat_id"]
                    if old_cat!=target.cat_id:
                        conn.execute("UPDATE events SET cat_id=? WHERE event_id=? AND household_id=?",(target.cat_id,event_id,DEFAULT_HOUSEHOLD_ID))
                        conn.execute("UPDATE photos SET cat_id=? WHERE event_id=? AND household_id=?",(target.cat_id,event_id,DEFAULT_HOUSEHOLD_ID))
                        conn.execute("INSERT INTO event_reassignments VALUES (?,?,?,?,?,?,?,?)",
                            (f"move_{uuid4().hex}",event_id,old_cat,target.cat_id,person["caregiver_id"],request.text,request.request_id,now.isoformat()))
                    event=_row_to_event(original).model_copy(update={"cat_id":target.cat_id})
                    recent=[_row_to_event(r) for r in conn.execute("SELECT * FROM events WHERE household_id=? AND cat_id=? AND event_id<>?",(DEFAULT_HOUSEHOLD_ID,target.cat_id,event_id))]
                    rule=analyze_event(target,event,recent)
                    field,question=next_question(state["event_type"],state["details"],state["unknown_fields"])
                    state["pending_field"]=field
                    state["last_response"]={**state.get("last_response",{}),"red_flags":[f.model_dump() for f in rule.red_flags],"follow_up":question,
                        "missing_fields":[k for k in state.get("last_response",{}).get("missing_fields",[]) if k not in {"confirmation","cat_id"}],"status":"awaiting_answer" if field else "completed"}
                    state["cat_id"]=target.cat_id;cat_id=target.cat_id;cat_name=target.name;state.pop("pending_action",None)
                    for key in ["pending_text","pending_occurred_at","pending_details","pending_event_type","pending_reporter"]:
                        state.pop(key,None)
                    speech=f"Corrected: this same observation is now recorded for {target.name}, not the previous cat. Its details, original time, and photos have been kept."
                    if rule.red_flags:speech+=" "+" ".join(f.message for f in rule.red_flags)
                    if question:speech+=" "+question
                    ui="observation_reassigned";extra={"from_cat_id":old_cat,"to_cat_id":target.cat_id,"event_id":event_id}
        elif plan.action in {"add_cat","select_cat","request_report","show_care_log"}:
            target=_find_cat(conn,plan.target_name) if plan.target_name else None
            if plan.action=="add_cat" and plan.target_name:
                target=_add_cat(conn,plan.target_name)
            if plan.target_name and target is None:
                state["pending_action"]={"action":"add_cat","target_name":plan.target_name}
                speech=f"There is no profile for {plan.target_name}. Should I create one? Please say yes or no.";confirm=True
            elif target is None and not cat_id:
                speech="Which cat is this for? Please name a cat, or ask me to add one."
                state["pending_action"]={"action":plan.action,"target_name":None,"report_days":plan.report_days};confirm=True
            else:
                if target and target.cat_id!=cat_id:
                    carry={key:value for key,value in state.items() if key in {"pending_text","pending_occurred_at","pending_details","pending_event_type","pending_reporter"}}
                    cat_id=target.cat_id;cat_name=target.name;state={**_blank(cat_id),**carry};session_id=f"sess_{uuid4().hex}"
                state.pop("pending_action",None)
                if plan.action=="request_report":
                    days=plan.report_days or 7
                    if not 1<=days<=365:raise ValueError("Report period must be between 1 and 365 days")
                    speech=f"Here is the requested {days}-day care report for {cat_name}. Nothing has been emailed or sent automatically.";ui="open_report";extra={"report_days":days,"download_format":("json" if re.search(r"\bjson\b",request.text,re.I) else "html") if re.search(r"download|export|下载|导出",request.text,re.I) else None}
                elif plan.action=="show_care_log":speech=f"Here is {cat_name}'s care log.";ui="open_care_log"
                else:speech=f"The profile for {cat_name} is ready. What would you like to record?";ui="profiles_updated"
        elif plan.action=="set_caregiver":
            if not plan.target_name:speech="What is the caregiver's name?"
            else:
                name=CaregiverCreate(name=plan.target_name).name
                existing=conn.execute("SELECT caregiver_id,name FROM caregivers WHERE household_id=? AND lower(name)=lower(?)",(DEFAULT_HOUSEHOLD_ID,name)).fetchone()
                if existing:person=dict(existing)
                else:
                    person={"caregiver_id":f"person_{uuid4().hex}","name":name}
                    conn.execute("INSERT INTO caregivers VALUES (?,?,?,?)",(person["caregiver_id"],DEFAULT_HOUSEHOLD_ID,name,now.isoformat()))
                speech=f"You are now recording as {person['name']}.";ui="caregiver_selected";state.pop("pending_action",None)
        elif plan.action=="new_observation":
            state=_blank(cat_id);session_id=f"sess_{uuid4().hex}"
            speech=f"Starting a separate observation{' for '+cat_name if cat_name else ''}. What did you notice?";ui="new_observation"
        elif plan.action=="photo_link":
            speech="Here is the photo upload link for this observation. This simulates a text message; no SMS or email has been sent." if state["event_id"] else "Please record an observation first, so the photo can be attached to it."
            ui="open_photo_link" if state["event_id"] else "none"
        elif plan.action=="show_record":speech="Here is the current observation.";ui="refresh_record"
        previous=state.get("last_response",{})
        field,follow_up=next_question(state["event_type"],state["details"],state["unknown_fields"]) if state["event_type"] else (None,None)
        normal_status="awaiting_answer" if field or not state["event_id"] else "completed"
        response=ConversationResponse(session_id=session_id,event_id=state["event_id"],cat_id=cat_id,cat_name=cat_name,
            caregiver_id=person["caregiver_id"],caregiver_name=person["name"],status="awaiting_confirmation" if confirm else normal_status,
            event_type=state["event_type"],details=state["details"],unknown_fields=state["unknown_fields"],
            missing_fields=["confirmation"] if confirm else missing_fields(state["event_type"],state["details"],state["unknown_fields"]) if state["event_type"] else [],follow_up=speech if confirm else follow_up,
            red_flags=previous.get("red_flags",[]),speech=speech,occurred_at=state["occurred_at"],
            upload_url=f"{PUBLIC_BASE_URL}/photos/upload?event_id={state['event_id']}" if state["event_id"] else None,
            extraction_provider=provider,ui_action=ui,action_payload=extra).model_dump(mode="json")
        state["active_caregiver_id"]=person["caregiver_id"]
        _save_turn(conn,state,response,session_id,request,now)
        return response
