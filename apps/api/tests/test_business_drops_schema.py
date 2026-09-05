from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.business_drops import BusinessDropCreateRequest


def _valid_drop(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    values = {
        "title": "Rooftop cinema",
        "category": "activity_entertainment",
        "drop_type": "solo",
        "latitude": -37.8119,
        "longitude": 144.9674,
        "max_capacity_participants": 10,
        "starts_at": now + timedelta(hours=1),
        "ends_at": now + timedelta(hours=4),
    }
    values.update(overrides)
    return values


def test_accepts_reasonable_values() -> None:
    request = BusinessDropCreateRequest(**_valid_drop())
    assert request.max_capacity_participants == 10


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_capacity_participants": 5000},
        {"min_group_size": 500},
        {"max_group_size": 500},
        {"discovery_radius_m": 500_000},
        {"discover_radius_m": 500_000},
        {"xp_reward_base": 1_000_000},
    ],
)
def test_rejects_unreasonably_large_values(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        BusinessDropCreateRequest(**_valid_drop(**overrides))
