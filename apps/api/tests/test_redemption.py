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
    reject_redemption,
)


def _business(business_id) -> MagicMock:
    business = MagicMock()
    business.id = business_id
    return business


def test_reject_redemption_releases_capacity_and_cancels_group(monkeypatch) -> None:
    business_id = uuid4()
    drop_id = uuid4()
    group_id = uuid4()
    redemption = Redemption(
        id=uuid4(),
        drop_id=drop_id,
        group_id=group_id,
        business_id=business_id,
        status=RedemptionStatus.checked_in,
    )
    group = Group(id=group_id, drop_id=drop_id, status=GroupStatus.checked_in)

    db = MagicMock(spec=Session)
    # In order: the redemption lookup, the group lookup, then
    # joined_member_count()'s own db.scalar(select(func.count())...) call.
    db.scalar.side_effect = [redemption, group, 3]
    released = {}
    monkeypatch.setattr(
        "app.services.redemption.release_capacity",
        lambda db_, drop_id_, count: released.update(drop_id=drop_id_, count=count),
    )

    result = reject_redemption(db, redemption.id, _business(business_id))

    assert result.status == RedemptionStatus.rejected
    assert result.confirmed_by == business_id
    assert group.status == GroupStatus.cancelled
    assert released == {"drop_id": drop_id, "count": 3}
    db.commit.assert_called_once()


def test_reject_redemption_skips_release_when_no_joined_members(monkeypatch) -> None:
    """An empty squad (everyone already left) has nothing to release —
    calling release_capacity with count=0 would raise (it requires count>0)."""
    business_id = uuid4()
    drop_id = uuid4()
    group_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=drop_id, group_id=group_id, business_id=business_id,
        status=RedemptionStatus.checked_in,
    )
    group = Group(id=group_id, drop_id=drop_id, status=GroupStatus.checked_in)

    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption, group, 0]
    release_capacity = MagicMock()
    monkeypatch.setattr("app.services.redemption.release_capacity", release_capacity)

    reject_redemption(db, redemption.id, _business(business_id))

    release_capacity.assert_not_called()


def test_reject_redemption_is_idempotent_when_already_rejected() -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.rejected,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    result = reject_redemption(db, redemption.id, _business(business_id))

    assert result is redemption
    db.commit.assert_not_called()


def test_reject_redemption_rejects_a_different_businesss_redemption() -> None:
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=uuid4(),
        status=RedemptionStatus.checked_in,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    with pytest.raises(HTTPException) as exc_info:
        reject_redemption(db, redemption.id, _business(uuid4()))

    assert exc_info.value.status_code == 403


def test_reject_redemption_rejects_a_confirmed_redemption() -> None:
    business_id = uuid4()
    redemption = Redemption(
        id=uuid4(), drop_id=uuid4(), group_id=uuid4(), business_id=business_id,
        status=RedemptionStatus.confirmed,
    )
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption]

    with pytest.raises(HTTPException) as exc_info:
        reject_redemption(db, redemption.id, _business(business_id))

    assert exc_info.value.status_code == 409


def test_within_check_in_range_false_without_a_known_location() -> None:
    user = User(id=uuid4(), last_location=None, last_location_at=None)
    drop = Drop(id=uuid4())

    assert _within_check_in_range(MagicMock(spec=Session), user, drop) is False


def test_within_check_in_range_false_when_location_is_stale() -> None:
    stale = datetime.now(timezone.utc) - timedelta(minutes=16)
    user = User(id=uuid4(), last_location="POINT(0 0)", last_location_at=stale)
    drop = Drop(id=uuid4())

    assert _within_check_in_range(MagicMock(spec=Session), user, drop) is False


def _member() -> MagicMock:
    return MagicMock()


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


def test_check_in_group_succeeds_within_range(monkeypatch) -> None:
    drop_id = uuid4()
    business_id = uuid4()
    group = Group(id=uuid4(), drop_id=drop_id, status=GroupStatus.ready)
    drop = Drop(id=drop_id, business_id=business_id)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, _member(), None]
    db.get.return_value = drop
    monkeypatch.setattr("app.services.redemption._within_check_in_range", lambda *a: True)

    redemption = check_in_group(db, group.id, User(id=uuid4()))

    assert redemption.status == RedemptionStatus.checked_in
    assert redemption.business_id == business_id
    assert group.status == GroupStatus.checked_in
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_check_in_group_is_idempotent_for_an_already_checked_in_squad(monkeypatch) -> None:
    """A second squad member claiming after the squad already checked in
    returns the existing Redemption instead of erroring or double-creating."""
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.checked_in)
    existing = Redemption(id=uuid4(), status=RedemptionStatus.checked_in)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, _member(), existing]

    result = check_in_group(db, group.id, User(id=uuid4()))

    assert result is existing
    db.commit.assert_not_called()
