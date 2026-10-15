from datetime import datetime, timedelta, timezone

from catnanny.domain.models import Cat, Event, EventType
from catnanny.domain.rules import analyze_event


def _cat(**overrides):
    data = {
        "household_id": "h1",
        "cat_id": "mochi",
        "name": "Mochi",
        "sex": "female",
    }
    data.update(overrides)
    return Cat(**data)


def _event(event_type, details, ts=None):
    return Event(
        household_id="h1",
        cat_id="mochi",
        ts=ts or datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc),
        type=event_type,
        details=details,
        reporter="Alex",
    )


def test_vomit_without_content_gets_follow_up_question():
    event = _event(EventType.VOMIT, {})

    result = analyze_event(_cat(), event, [])

    assert result.follow_up == "Was it food, hairball, liquid, or foam?"
    assert result.red_flags == []


def test_vomit_with_blood_flags_call_vet_today():
    event = _event(EventType.VOMIT, {"content": "food", "has_blood": True})

    result = analyze_event(_cat(), event, [])

    assert result.red_flags[0].level == "today"
    assert result.red_flags[0].code == "vomit_blood"


def test_third_vomit_in_24_hours_flags_call_vet_today():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    event = _event(EventType.VOMIT, {"content": "food", "has_blood": False}, now)
    recent = [
        _event(EventType.VOMIT, {"content": "food"}, now - timedelta(hours=2)),
        _event(EventType.VOMIT, {"content": "liquid"}, now - timedelta(hours=6)),
    ]

    result = analyze_event(_cat(), event, recent)

    assert any(flag.code == "vomit_three_times_24h" for flag in result.red_flags)


def test_male_cat_straining_without_urine_is_emergency():
    event = _event(EventType.LITTER, {"straining": True, "passing_urine": False})

    result = analyze_event(_cat(sex="male"), event, [])

    assert result.red_flags[0].level == "emergency"
    assert result.red_flags[0].code == "male_cat_not_urinating"


def test_future_events_and_current_event_are_not_counted_as_history():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    event = _event(EventType.VOMIT, {"content": "food", "has_blood": False}, now)
    future = _event(EventType.VOMIT, {}, now + timedelta(hours=1))
    result = analyze_event(_cat(), event, [event, future])
    assert not any(flag.code == "vomit_three_times_24h" for flag in result.red_flags)
