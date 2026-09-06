from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.drops import Drop
from app.models.groups import Group, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.models.users import User
from app.services.redemption import (
    _within_check_in_range,
    check_in_group,
    dispute_redemption,
)


def _business(business_id) -> MagicMock:
    business = MagicMock()
    business.id = business_id
    return business


def _member() -> MagicMock:
    return MagicMock()


def test_within_check_in_range_false_without_a_known_location() -> None:
    user = User(id=uuid4(), last_location=None, last_location_at=None)
    drop = Drop(id=uuid4())

    assert _within_check_in_range(MagicMock(spec=Session), user, drop) is False


def test_within_check_in_range_false_when_location_is_stale() -> None:
    stale = datetime.now(timezone.utc) - timedelta(minutes=16)
    user = User(id=uuid4(), last_location="POINT(0 0)", last_location_at=stale)
    drop = Drop(id=uuid4())

    assert _within_check_in_range(MagicMock(spec=Session), user, drop) is False


def test_check_in_group_requires_membership() -> None:
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.ready)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, None]  # group lookup, membership lookup (not found)

    with pytest.raises(HTTPException) as exc_info:
        check_in_group(db, group.id, User(id=uuid4()))

    assert exc_info.value.status_code == 403


def test_check_in_group_requires_ready_status() -> None:
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.forming)
    db = MagicMock(spec=Session)
    # group lookup, membership lookup (found), existing-redemption lookup (none)
    db.scalar.side_effect = [group, _member(), None]

    with pytest.raises(HTTPException) as exc_info:
        check_in_group(db, group.id, User(id=uuid4()))

    assert exc_info.value.status_code == 409


def test_check_in_group_requires_proximity(monkeypatch) -> None:
    drop_id = uuid4()
    group = Group(id=uuid4(), drop_id=drop_id, status=GroupStatus.ready)
    drop = Drop(id=drop_id, business_id=uuid4())
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, _member(), None]
    db.get.return_value = drop
    monkeypatch.setattr("app.services.redemption._within_check_in_range", lambda *a: False)

    with pytest.raises(HTTPException) as exc_info:
        check_in_group(db, group.id, User(id=uuid4()))

    assert exc_info.value.status_code == 403
    assert "closer" in exc_info.value.detail


def test_check_in_group_auto_confirms_within_range(monkeypatch) -> None:
    """Check-in has no business approval gate — a proximity-passing claim
    goes straight to confirmed, and the Group straight to completed."""
    drop_id = uuid4()
    business_id = uuid4()
    group = Group(id=uuid4(), drop_id=drop_id, status=GroupStatus.ready)
    drop = Drop(id=drop_id, business_id=business_id)
    db = MagicMock(spec=Session)
    # group, membership, existing-redemption (none), joined_member_count's own scalar
    db.scalar.side_effect = [group, _member(), None, 3]
    db.get.return_value = drop
    monkeypatch.setattr("app.services.redemption._within_check_in_range", lambda *a: True)

    redemption = check_in_group(db, group.id, User(id=uuid4()))

    assert redemption.status == RedemptionStatus.confirmed
    assert redemption.business_id == business_id
    assert redemption.confirmed_by == business_id
    assert redemption.participant_count == 3
    assert group.status == GroupStatus.completed
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_check_in_group_is_idempotent_for_an_already_confirmed_squad() -> None:
    """A second squad member claiming after the squad already auto-confirmed
    returns the existing Redemption instead of erroring or double-creating."""
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.completed)
    existing = Redemption(id=uuid4(), status=RedemptionStatus.confirmed)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, _member(), existing]

    result = check_in_group(db, group.id, User(id=uuid4()))

    assert result is existing
    db.commit.assert_not_called()


def test_dispute_redemption_releases_capacity(monkeypatch) -> None:
    business_id = uuid4()
    drop_id = uuid4()
    redemption = Redemption(
        id=uuid4(),
        drop_id=drop_id,
        group_id=uuid4(),
        business_id=business_id,
        status=RedemptionStatus.confirmed,
        confirmed_at=datetime.now(timezone.utc),
        participant_count=3,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]
    released = {}
    monkeypatch.setattr(
        "app.services.redemption.release_capacity",
        lambda db_, drop_id_, count: released.update(drop_id=drop_id_, count=count),
    )

    result = dispute_redemption(db, redemption.id, _business(business_id))

    assert result.disputed_at is not None
    assert released == {"drop_id": drop_id, "count": 3}
    db.commit.assert_called_once()


def test_dispute_redemption_skips_release_with_no_recorded_participants(monkeypatch) -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.confirmed, confirmed_at=datetime.now(timezone.utc),
        participant_count=None,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]
    release_capacity = MagicMock()
    monkeypatch.setattr("app.services.redemption.release_capacity", release_capacity)

    dispute_redemption(db, redemption.id, _business(business_id))

    release_capacity.assert_not_called()


def test_dispute_redemption_is_idempotent_when_already_disputed() -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.confirmed, confirmed_at=datetime.now(timezone.utc),
        disputed_at=datetime.now(timezone.utc),
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    result = dispute_redemption(db, redemption.id, _business(business_id))

    assert result is redemption
    db.commit.assert_not_called()


def test_dispute_redemption_rejects_a_different_businesss_redemption() -> None:
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=uuid4(),
        status=RedemptionStatus.confirmed, confirmed_at=datetime.now(timezone.utc),
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    with pytest.raises(HTTPException) as exc_info:
        dispute_redemption(db, redemption.id, _business(uuid4()))

    assert exc_info.value.status_code == 403


def test_dispute_redemption_requires_confirmed_status() -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.pending,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    with pytest.raises(HTTPException) as exc_info:
        dispute_redemption(db, redemption.id, _business(business_id))

    assert exc_info.value.status_code == 409


def test_dispute_redemption_rejects_after_the_window_has_passed() -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.confirmed,
        confirmed_at=datetime.now(timezone.utc) - timedelta(hours=25),
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    with pytest.raises(HTTPException) as exc_info:
        dispute_redemption(db, redemption.id, _business(business_id))

    assert exc_info.value.status_code == 409
    assert "window" in exc_info.value.detail
