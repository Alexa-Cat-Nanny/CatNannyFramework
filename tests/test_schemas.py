import pytest
from pydantic import ValidationError
from catnanny.domain.schemas import ConversationRequest, VomitDetails, AppetiteDetails


@pytest.mark.parametrize("data", [{"episode_count": -1}, {"episode_count": 1.5},
    {"has_blood": "false"}, {"has_blood": 0}, {"unexpected": True}, {"content": "diagnosis"}])
def test_reject_invalid_observations(data):
    with pytest.raises(ValidationError):
        VomitDetails.model_validate(data)


def test_unknown_is_distinct_from_false():
    assert VomitDetails().has_blood is None
    assert VomitDetails(has_blood=False).has_blood is False


def test_duration_and_timezone_validation():
    with pytest.raises(ValidationError):
        AppetiteDetails(hours_since_food=-1)
    with pytest.raises(ValidationError):
        ConversationRequest(request_id="x", occurred_at="2026-10-14T12:00:00")
