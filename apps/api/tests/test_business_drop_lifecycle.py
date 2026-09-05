from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.drops import Drop, DropStatus
from app.services.drop_lifecycle import cancel_drop, pause_drop, publish_drop, resume_drop


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
