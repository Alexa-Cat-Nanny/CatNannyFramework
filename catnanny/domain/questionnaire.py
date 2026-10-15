"""Observation questions, separate from veterinary safety rules."""
QUESTIONS = {
    "vomit": [
        ("content", "Was it food, a hairball, liquid, or foam?"),
        ("has_blood", "Did you see any blood?"),
        ("episode_count", "How many vomiting episodes are you recording?"),
        ("low_energy", "Did you notice lower energy than usual?"),
    ],
    "appetite": [
        ("status", "Is your cat not eating at all, or eating less than usual?"),
        ("hours_since_food", "About how many hours since your cat last ate normally?"),
    ],
}


def missing_fields(event_type, details, unknown_fields):
    return [key for key, _ in QUESTIONS[event_type]
            if details.get(key) is None and key not in unknown_fields]


def next_question(event_type, details, unknown_fields):
    missing = missing_fields(event_type, details, unknown_fields)
    if not missing:
        return None, None
    key = missing[0]
    return key, dict(QUESTIONS[event_type])[key]
