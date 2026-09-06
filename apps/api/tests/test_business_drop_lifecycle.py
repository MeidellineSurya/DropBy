from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.drops import Drop, DropRarity, DropStatus
from app.services.drop_lifecycle import (
    cancel_drop,
    compute_rarity,
    compute_xp_reward,
    delete_drop,
    describe_capacity_failure,
    expire_due,
    pause_drop,
    publish_drop,
    resume_drop,
)


def make_drop(**overrides) -> Drop:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid4(),
        business_id=uuid4(),
        status=DropStatus.draft,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
    )
    defaults.update(overrides)
    return Drop(**defaults)


def test_publish_drop_stages_scheduled_when_starts_in_future() -> None:
    db = MagicMock(spec=Session)
    drop = make_drop()
    db.scalar.return_value = drop

    result = publish_drop(db, drop.id, drop.business_id)

    assert result is drop
    assert drop.status == DropStatus.scheduled
    db.commit.assert_called_once_with()


def test_publish_drop_stages_active_when_starts_now_or_past() -> None:
    db = MagicMock(spec=Session)
    now = datetime.now(timezone.utc)
    drop = make_drop(starts_at=now - timedelta(minutes=1))
    db.scalar.return_value = drop

    publish_drop(db, drop.id, drop.business_id)

    assert drop.status == DropStatus.active


def test_publish_drop_rejects_already_expired_drop() -> None:
    db = MagicMock(spec=Session)
    now = datetime.now(timezone.utc)
    drop = make_drop(starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1))
    db.scalar.return_value = drop

    with pytest.raises(ValueError, match="cannot be published"):
        publish_drop(db, drop.id, drop.business_id)
    db.commit.assert_not_called()


def test_publish_drop_returns_none_when_not_found_or_not_draft() -> None:
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    assert publish_drop(db, uuid4(), uuid4()) is None
    db.commit.assert_not_called()


def test_pause_drop_returns_none_when_no_matching_active_drop() -> None:
    db = MagicMock(spec=Session)
    db.execute.return_value.rowcount = 0

    assert pause_drop(db, uuid4(), uuid4()) is None
    db.commit.assert_not_called()
    db.get.assert_not_called()


def test_pause_then_resume_round_trip() -> None:
    db = MagicMock(spec=Session)
    drop = make_drop(status=DropStatus.paused)
    db.execute.return_value.rowcount = 1
    db.get.return_value = drop

    paused = pause_drop(db, drop.id, drop.business_id)
    resumed = resume_drop(db, drop.id, drop.business_id)

    assert paused is drop
    assert resumed is drop
    assert db.commit.call_count == 2


def test_cancel_drop_returns_none_when_not_owned_or_terminal() -> None:
    db = MagicMock(spec=Session)
    db.execute.return_value.rowcount = 0

    assert cancel_drop(db, uuid4(), uuid4()) is None
    db.commit.assert_not_called()


def test_cancel_drop_returns_cascaded_group_ids() -> None:
    db = MagicMock(spec=Session)
    db.execute.return_value.rowcount = 1
    cascaded_ids = [uuid4(), uuid4()]
    db.scalars.return_value.all.return_value = cascaded_ids

    result = cancel_drop(db, uuid4(), uuid4())

    assert result == cascaded_ids
    db.commit.assert_called_once_with()


def test_delete_drop_returns_false_when_not_found_or_not_owned() -> None:
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    assert delete_drop(db, uuid4(), uuid4()) is False
    db.commit.assert_not_called()
    db.delete.assert_not_called()


def test_delete_drop_rejects_a_drop_with_squad_activity() -> None:
    # A real Group implies a real Redemption and real awarded XP downstream
    # — deleting it out from under that history isn't something one click
    # should do. cancel_drop is the right tool once there's real activity.
    db = MagicMock(spec=Session)
    drop = make_drop()
    db.scalar.side_effect = [drop, 2]  # drop lookup, then the squad-count query

    with pytest.raises(ValueError, match="2 squad"):
        delete_drop(db, drop.id, drop.business_id)
    db.commit.assert_not_called()
    db.delete.assert_not_called()


def test_delete_drop_removes_a_drop_with_no_squad_activity() -> None:
    db = MagicMock(spec=Session)
    drop = make_drop()
    db.scalar.side_effect = [drop, 0]

    result = delete_drop(db, drop.id, drop.business_id)

    assert result is True
    db.delete.assert_called_once_with(drop)
    db.commit.assert_called_once_with()


def test_expire_due_gives_forming_and_ready_squads_different_reasons() -> None:
    """Two separate UPDATEs (not one) so a squad that never found enough
    people gets a different cancelled_reason than one that was ready but
    ran out of time to check in — see services/drop_lifecycle.expire_due."""
    db = MagicMock(spec=Session)
    drop_ids = [uuid4()]
    forming_group_ids = [uuid4()]
    ready_group_ids = [uuid4(), uuid4()]

    drops_result = MagicMock()
    drops_result.all.return_value = drop_ids
    forming_result = MagicMock()
    forming_result.all.return_value = forming_group_ids
    ready_result = MagicMock()
    ready_result.all.return_value = ready_group_ids
    db.scalars.side_effect = [drops_result, forming_result, ready_result]

    returned_drop_ids, returned_group_ids = expire_due(db)

    assert returned_drop_ids == drop_ids
    assert returned_group_ids == forming_group_ids + ready_group_ids
    assert db.scalars.call_count == 3
    db.commit.assert_called_once_with()


def test_expire_due_skips_group_queries_when_no_drops_expired() -> None:
    db = MagicMock(spec=Session)
    drops_result = MagicMock()
    drops_result.all.return_value = []
    db.scalars.return_value = drops_result

    returned_drop_ids, returned_group_ids = expire_due(db)

    assert returned_drop_ids == []
    assert returned_group_ids == []
    assert db.scalars.call_count == 1


def test_describe_capacity_failure_distinguishes_paused_from_full() -> None:
    """The race this covers: reserve_capacity() only matches status ==
    active, so a squad that crosses min_required the instant a business
    pauses the Drop fails the same way a genuinely sold-out Drop would.
    Members deserve to be told which one actually happened."""
    db = MagicMock(spec=Session)
    paused_drop = make_drop(status=DropStatus.paused)
    db.get.return_value = paused_drop

    assert describe_capacity_failure(db, paused_drop.id) == (
        "This Drop is temporarily paused by the business."
    )


def test_describe_capacity_failure_reports_genuinely_full() -> None:
    db = MagicMock(spec=Session)
    active_drop = make_drop(status=DropStatus.active)
    db.get.return_value = active_drop

    assert describe_capacity_failure(db, active_drop.id) == (
        "This Drop has reached full capacity."
    )


def test_describe_capacity_failure_reports_ended_drop() -> None:
    db = MagicMock(spec=Session)
    now = datetime.now(timezone.utc)
    ended_drop = make_drop(
        status=DropStatus.active,
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(minutes=1),
    )
    db.get.return_value = ended_drop

    assert describe_capacity_failure(db, ended_drop.id) == "This Drop has ended."


def test_describe_capacity_failure_handles_missing_drop() -> None:
    db = MagicMock(spec=Session)
    db.get.return_value = None

    assert describe_capacity_failure(db, uuid4()) == "This Drop no longer exists."


@pytest.mark.parametrize(
    ("discount_percent", "expected"),
    [
        (1, DropRarity.common),
        (19, DropRarity.common),
        (20, DropRarity.uncommon),
        (39, DropRarity.uncommon),
        (40, DropRarity.rare),
        (59, DropRarity.rare),
        (60, DropRarity.epic),
        (79, DropRarity.epic),
        (80, DropRarity.legendary),
        (100, DropRarity.legendary),
    ],
)
def test_compute_rarity_tiers_by_discount_depth(
    discount_percent: int, expected: DropRarity
) -> None:
    # A large-venue, solo-friendly Drop — discount alone should decide the
    # tier with no scarcity/commitment bump.
    assert compute_rarity(discount_percent, min_group_size=1, venue_capacity=100) == expected


def test_compute_rarity_bumps_a_tier_for_a_small_venue() -> None:
    # 30% off would normally be uncommon, but a business with only 4
    # registered seats total is genuinely scarce — matches the brief's
    # "Epic: very limited" framing.
    assert compute_rarity(30, min_group_size=1, venue_capacity=4) == DropRarity.rare


def test_compute_rarity_bumps_a_tier_for_a_large_required_group() -> None:
    # A raid-sized commitment reads as a bigger ask than the discount alone.
    assert compute_rarity(30, min_group_size=8, venue_capacity=100) == DropRarity.rare


def test_compute_rarity_never_bumps_past_legendary() -> None:
    assert (
        compute_rarity(90, min_group_size=10, venue_capacity=2) == DropRarity.legendary
    )


def test_compute_rarity_is_not_gameable_by_a_small_per_drop_capacity() -> None:
    # The loophole this closes: previously, scarcity was judged from the
    # freely-editable per-Drop max_capacity_participants, so a business
    # could declare an artificially small Drop capacity for a free rarity
    # bump at zero real cost, regardless of their actual venue size. Now
    # scarcity is judged from venue_capacity (declared once at registration),
    # so a large-venue business gets no bump just by capping one Drop small.
    assert compute_rarity(30, min_group_size=1, venue_capacity=200) == DropRarity.uncommon


def test_compute_rarity_is_never_business_declared() -> None:
    # There is no way to pass a rarity into create_drop at all anymore —
    # confirmed at the schema layer too, see test_business_drops_schema.py.
    import inspect

    from app.services.drop_lifecycle import create_drop

    assert "rarity" not in inspect.signature(create_drop).parameters


@pytest.mark.parametrize(
    ("rarity", "expected_xp"),
    [
        (DropRarity.common, 10),
        (DropRarity.uncommon, 20),
        (DropRarity.rare, 40),
        (DropRarity.epic, 80),
        (DropRarity.legendary, 160),
    ],
)
def test_compute_xp_reward_doubles_per_tier(rarity: DropRarity, expected_xp: int) -> None:
    assert compute_xp_reward(rarity) == expected_xp


def test_compute_xp_reward_is_never_business_declared() -> None:
    # Same reasoning as rarity: a free xp_reward_base input let a business
    # pair a trivial discount with a huge XP payout. There is no way to pass
    # xp_reward_base into create_drop at all anymore.
    import inspect

    from app.services.drop_lifecycle import create_drop

    assert "xp_reward_base" not in inspect.signature(create_drop).parameters
