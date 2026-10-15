import pytest
from catnanny.services.extraction_service import detect_type, extract


@pytest.mark.parametrize("text,expected", [("猫今天吐了两次", "vomit"),
    ("Mochi threw up", "vomit"), ("猫不吃饭", "appetite"),
    ("猫不吃饭而且吐了", None), ("猫打喷嚏", None), ("猫没有吐", None)])
def test_classification(text, expected):
    assert detect_type(text) == expected


def test_count_and_negative_blood():
    assert extract("吐了两次，没有血", "vomit")[0] == {"episode_count": 2, "has_blood": False}


def test_short_answer_uses_pending_question():
    assert extract("没有", "vomit", "has_blood")[0] == {"has_blood": False}
    assert extract("没有", "vomit", "low_energy")[0] == {"low_energy": False}
    assert extract("没有", "vomit")[0] == {}


def test_unknown_is_never_negative():
    assert extract("不知道有没有血", "vomit", "has_blood") == ({}, "has_blood")


def test_appetite_duration():
    assert extract("12小时", "appetite", "hours_since_food")[0] == {"hours_since_food": 12.0}


def test_negative_numbers_are_not_silently_made_positive():
    assert extract("-2小时", "appetite", "hours_since_food")[0]["hours_since_food"] == -2.0
    assert extract("-2次", "vomit", "episode_count")[0]["episode_count"] == -2
