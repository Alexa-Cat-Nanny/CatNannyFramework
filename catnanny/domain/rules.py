from datetime import timedelta

from catnanny.domain.models import Cat, Event, EventType, RedFlag, RuleResult


def analyze_event(cat: Cat, event: Event, recent_events: list[Event]) -> RuleResult:
    """Return deterministic follow-up questions and conservative safety flags."""
    if event.type == EventType.VOMIT:
        return _analyze_vomit(event, recent_events)
    if event.type == EventType.APPETITE:
        return _analyze_appetite(event)
    if event.type == EventType.LITTER:
        return _analyze_litter(cat, event)
    if event.type == EventType.ENERGY:
        return _analyze_energy(event)
    return RuleResult()


def _analyze_vomit(event: Event, recent_events: list[Event]) -> RuleResult:
    flags: list[RedFlag] = []
    content = event.details.get("content")
    has_blood = event.details.get("has_blood")
    low_energy = event.details.get("low_energy")

    follow_up = None
    if not content:
        follow_up = "Was it food, hairball, liquid, or foam?"
    elif has_blood is None:
        follow_up = "Did you see any blood?"

    if has_blood:
        flags.append(
            RedFlag(
                level="today",
                code="vomit_blood",
                message="Please call your vet today. Vomit with blood is worth prompt veterinary advice.",
            )
        )

    if low_energy:
        flags.append(
            RedFlag(
                level="today",
                code="vomit_low_energy",
                message="Please call your vet today. Vomiting together with low energy can be concerning.",
            )
        )

    vomiting_today = [
        item
        for item in recent_events
        if item.event_id != event.event_id and item.type == EventType.VOMIT
        and timedelta(0) <= event.ts - item.ts <= timedelta(hours=24)
    ]
    if len(vomiting_today) >= 2:
        flags.append(
            RedFlag(
                level="today",
                code="vomit_three_times_24h",
                message="Please call your vet today. This is at least the third vomiting episode in 24 hours.",
            )
        )

    return RuleResult(follow_up=follow_up, red_flags=flags)


def _analyze_appetite(event: Event) -> RuleResult:
    status = event.details.get("status")
    hours_since_food = event.details.get("hours_since_food")

    if status in {"not_eating", "none"} and hours_since_food is None:
        return RuleResult(follow_up="When did your cat last eat normally?")

    if isinstance(hours_since_food, int | float) and hours_since_food >= 24:
        return RuleResult(
            red_flags=[
                RedFlag(
                    level="today",
                    code="not_eating_24h",
                    message="Please call your vet today. A cat not eating for more than 24 hours should be checked.",
                )
            ]
        )

    return RuleResult()


def _analyze_litter(cat: Cat, event: Event) -> RuleResult:
    straining = event.details.get("straining")
    passing_urine = event.details.get("passing_urine")

    if straining is None:
        return RuleResult(follow_up="Was your cat straining in the litter box?")
    if passing_urine is None:
        return RuleResult(follow_up="Was your cat passing urine?")

    is_male = cat.sex == "male"
    if is_male and straining and not passing_urine:
        return RuleResult(
            red_flags=[
                RedFlag(
                    level="emergency",
                    code="male_cat_not_urinating",
                    message="This can be an emergency. Please contact a vet or emergency clinic now.",
                )
            ]
        )

    return RuleResult()


def _analyze_energy(event: Event) -> RuleResult:
    level = event.details.get("level")
    if not level:
        return RuleResult(follow_up="Is your cat hiding, weak, or just sleeping more than usual?")
    return RuleResult()
