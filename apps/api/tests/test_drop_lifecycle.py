from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.drops import DropCategory, DropRarity, DropStatus, DropType
from app.services.drop_lifecycle import create_drop


def valid_values() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "business_id": uuid4(),
        "title": "  Rooftop cinema  ",
        "category": DropCategory.activity_entertainment,
        "drop_type": DropType.squad,
        "latitude": -37.8119,
        "longitude": 144.9674,
        "max_capacity_participants": 12,
        "starts_at": now + timedelta(hours=1),
        "ends_at": now + timedelta(hours=4),
        "min_group_size": 2,
        "max_group_size": 4,
        "discount_percent": 40,
    }


def test_create_drop_stages_valid_scheduled_drop() -> None:
    db = MagicMock(spec=Session)

    drop = create_drop(db, **valid_values(), publish=True)

    assert drop.title == "Rooftop cinema"
    assert drop.status == DropStatus.scheduled
    assert drop.reserved_count == 0
    # Computed from discount_percent=40 (rare tier), not accepted as input —
    # there's no rarity kwarg on create_drop at all anymore.
    assert drop.rarity == DropRarity.rare
    # XP is computed from that same rarity — also not an input kwarg.
    assert drop.xp_reward_base == 40
    db.add.assert_called_once_with(drop)
    db.flush.assert_called_once_with()


def test_create_drop_can_create_draft_without_publishing() -> None:
    db = MagicMock(spec=Session)

    drop = create_drop(db, **valid_values())

    assert drop.status == DropStatus.draft


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"ends_at": datetime.now(timezone.utc)}, "ends_at must be after"),
        ({"discover_radius_m": 200, "reveal_radius_m": 100}, "radii must"),
        ({"max_capacity_participants": 1}, "capacity must"),
        ({"latitude": -91}, "invalid latitude"),
        ({"discount_percent": 0}, "discount_percent must be"),
        ({"discount_percent": 101}, "discount_percent must be"),
    ],
)
def test_create_drop_rejects_invalid_lifecycle_input(
    override: dict, message: str
) -> None:
    db = MagicMock(spec=Session)
    values = valid_values()
    values.update(override)

    with pytest.raises(ValueError, match=message):
        create_drop(db, **values)

    db.add.assert_not_called()
