"""Deterministic local extractor for documented Chinese/English demo phrases.

This is deliberately limited: unsupported language is clarified, never guessed.
Replace this boundary with a model adapter later; validation still runs afterward.
"""
import re

UNKNOWN = re.compile(r"不知道|不清楚|不确定|没注意|unknown|not sure|don't know", re.I)
NUMBERS = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
           "七": 7, "八": 8, "九": 9, "十": 10, "一次": 1}


def number(token):
    return NUMBERS[token] if token in NUMBERS else float(token)


def detect_type(text):
    matches = []
    if re.search(r"没(?:有)?(?:呕)?吐|没有发生呕吐|did not vomit|didn't vomit|not vomiting", text, re.I):
        return None
    if re.search(r"吐|vomit|threw up|throwing up", text, re.I):
        matches.append("vomit")
    if re.search(r"不吃|没吃|吃得少|食欲|not eating|won't eat|eating less", text, re.I):
        matches.append("appetite")
    return matches[0] if len(matches) == 1 else None


def extract(text, event_type, pending_field=None):
    lowered = text.lower().strip()
    result = {}
    if UNKNOWN.search(text):
        return result, pending_field
    if event_type == "vomit":
        for value, pattern in [("hairball", r"毛球|hairball"), ("foam", r"泡沫|foam"),
                               ("food", r"食物|粮|food"), ("liquid", r"液体|liquid")]:
            if re.search(pattern, lowered):
                result["content"] = value
                break
        if re.search(r"没(?:有)?血|没有看到血|没看到血|无血|no blood|without blood", lowered):
            result["has_blood"] = False
        elif re.search(r"有血|看到血|带血|blood", lowered):
            result["has_blood"] = True
        if re.search(r"精神(?:没有变差|没变差|正常|很好|还好)|no low energy|normal energy|energy (?:is )?normal|not lethargic", lowered):
            result["low_energy"] = False
        elif re.search(r"精神(?:不好|差|变差)|没精神|low energy|lethargic", lowered):
            result["low_energy"] = True
        count = re.search(r"(-?\d+(?:\.\d+)?|[一两二三四五六七八九十])\s*(?:次|times?\b)", lowered)
        if count:
            result["episode_count"] = number(count[1])
        elif re.search(r"\b(?:once|twice|three times)\b",lowered):
            result["episode_count"] = 1 if re.search(r"\bonce\b",lowered) else 2 if re.search(r"\btwice\b",lowered) else 3
    elif event_type == "appetite":
        if re.search(r"不吃|没吃|not eating|won't eat", lowered):
            result["status"] = "not_eating"
        elif re.search(r"吃得少|吃得比平时少|eating less", lowered):
            result["status"] = "eating_less"
        elif re.search(r"正常进食了|吃饭正常|eating normally", lowered):
            result["status"] = "normal"
        hours = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:个?小时|hours?\b)", lowered)
        if hours:
            result["hours_since_food"] = float(hours[1])
    # Short answers are interpreted ONLY against the persisted pending question.
    short = lowered.strip(" 。.!！")
    if pending_field in {"has_blood", "low_energy"} and pending_field not in result:
        if short in {"没有", "没", "否", "不是", "no", "false"}:
            result[pending_field] = False
        elif short in {"有", "是", "yes", "true"}:
            result[pending_field] = True
    if pending_field in {"episode_count", "hours_since_food"} and pending_field not in result:
        if re.fullmatch(r"-?\d+(?:\.\d+)?|[一两二三四五六七八九十]", short):
            result[pending_field] = number(short)
    if "episode_count" in result and float(result["episode_count"]).is_integer():
        result["episode_count"] = int(result["episode_count"])
    return result, None
