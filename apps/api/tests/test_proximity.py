from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.businesses import Business
from app.models.drops import (
    Drop,
    DropCategory,
    DropRarity,
    DropStatus,
    DropType,
    DropViewStage,
)
from app.services.proximity import snapshot_for, stage_for_distance


def sample_drop() -> Drop:
    return Drop(
        id=uuid4(),
        business_id=uuid4(),
        title="Rare Korean BBQ Drop",
        description="40% off dinner",
        category=DropCategory.food_dining,
        rarity=DropRarity.rare,
        drop_type=DropType.squad,
        min_group_size=4,
        max_group_size=6,
        discovery_radius_m=700,
        reveal_radius_m=180,
        discover_radius_m=60,
        max_capacity_participants=12,
        reserved_count=0,
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status=DropStatus.active,
    )


def sample_business() -> Business:
    return Business(
        id=uuid4(),
        name="Secret Restaurant",
        category="food_dining",
        address="Hidden Lane",
        owner_email="owner@example.com",
        password_hash="not-used",
    )


def test_detect_hides_sensitive_fields() -> None:
    drop = sample_drop()
    stage = stage_for_distance(500, drop)
    payload = snapshot_for(drop, sample_business(), 500, stage).model_dump(
        exclude_none=True
    )
    assert stage == DropViewStage.detect
    assert payload["distance_m"] == 500
    assert "business_name" not in payload
    assert "description" not in payload
    assert "address" not in payload


def test_reveal_adds_category_but_not_business() -> None:
    drop = sample_drop()
    stage = stage_for_distance(150, drop)
    payload = snapshot_for(drop, sample_business(), 150, stage).model_dump(
        exclude_none=True
    )
    assert stage == DropViewStage.reveal
    assert payload["category"] == DropCategory.food_dining
    assert "business_name" not in payload


def test_discover_reveals_offer_and_assemble_action() -> None:
    drop = sample_drop()
    stage = stage_for_distance(50, drop)
    payload = snapshot_for(drop, sample_business(), 50, stage).model_dump(
        exclude_none=True
    )
    assert stage == DropViewStage.discover
    assert payload["business_name"] == "Secret Restaurant"
    assert payload["description"] == "40% off dinner"
    assert payload["can_assemble"] is True


def test_discover_stays_unlocked_after_moving_away() -> None:
    assert (
        stage_for_distance(500, sample_drop(), discover_unlocked=True)
        == DropViewStage.discover
    )
