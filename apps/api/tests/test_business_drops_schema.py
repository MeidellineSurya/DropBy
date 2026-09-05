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
        "discount_percent": 30,
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
        {"discount_percent": 0},
        {"discount_percent": 101},
    ],
)
def test_rejects_unreasonably_large_values(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        BusinessDropCreateRequest(**_valid_drop(**overrides))


def test_rarity_is_not_a_field_on_the_create_request() -> None:
    # Rarity used to be a free-text-adjacent enum a business picked directly;
    # it's now always computed (see compute_rarity), so accepting one here
    # at all would silently do nothing useful and confuse API consumers.
    request = BusinessDropCreateRequest(**_valid_drop())
    assert not hasattr(request, "rarity")


def test_xp_reward_base_is_not_a_field_on_the_create_request() -> None:
    # Same reasoning as rarity: a business-set XP value had nothing tying it
    # to the offer either. It's computed from rarity (compute_xp_reward).
    request = BusinessDropCreateRequest(**_valid_drop())
    assert not hasattr(request, "xp_reward_base")
