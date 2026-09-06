from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.drops import Drop
from app.models.groups import Group, GroupMember, GroupMemberStatus, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.models.users import User
from app.services.redemption import (
    dispute_redemption,
    get_squad_qr,
    scan_squad_qr,
    sign_squad_qr,
    verify_squad_qr,
)


def _business(business_id) -> MagicMock:
    business = MagicMock()
    business.id = business_id
    return business


def _member() -> MagicMock:
    return MagicMock()


def test_sign_and_verify_squad_qr_roundtrip() -> None:
    token = sign_squad_qr("group-123", "drop-456", "business-789")

    claims = verify_squad_qr(token)

    assert claims == {"group_id": "group-123", "drop_id": "drop-456", "business_id": "business-789"}


def test_verify_squad_qr_rejects_tampered_signature() -> None:
    token = sign_squad_qr("group-123", "drop-456", "business-789")
    group_id, drop_id, _business_id, iat, nonce, signature = token.split(":")
    tampered = f"{group_id}:{drop_id}:attacker-business:{iat}:{nonce}:{signature}"

    with pytest.raises(ValueError, match="invalid QR signature"):
        verify_squad_qr(tampered)


def test_verify_squad_qr_rejects_malformed_token() -> None:
    with pytest.raises(ValueError, match="malformed QR token"):
        verify_squad_qr("not-a-real-token")


def test_repeated_signing_produces_independently_valid_tokens() -> None:
    """Re-fetching the code (get_squad_qr) any number of times must never
    invalidate a copy already displayed to staff."""
    first = sign_squad_qr("group-123", "drop-456", "business-789")
    second = sign_squad_qr("group-123", "drop-456", "business-789")

    assert first != second
    assert verify_squad_qr(first) == verify_squad_qr(second)


def test_get_squad_qr_requires_membership() -> None:
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.ready)
    db = MagicMock(spec=Session)
    db.get.return_value = group
    db.scalar.return_value = None  # membership lookup: not found

    with pytest.raises(HTTPException) as exc_info:
        get_squad_qr(db, group.id, User(id=uuid4()))

    assert exc_info.value.status_code == 403


def test_get_squad_qr_requires_ready_status() -> None:
    group = Group(id=uuid4(), drop_id=uuid4(), status=GroupStatus.forming)
    db = MagicMock(spec=Session)
    db.get.return_value = group
    db.scalar.return_value = uuid4()  # membership found

    with pytest.raises(HTTPException) as exc_info:
        get_squad_qr(db, group.id, User(id=uuid4()))

    assert exc_info.value.status_code == 409


def test_get_squad_qr_returns_a_valid_token_when_ready() -> None:
    drop_id = uuid4()
    business_id = uuid4()
    group = Group(id=uuid4(), drop_id=drop_id, status=GroupStatus.ready)
    drop = Drop(id=drop_id, business_id=business_id)
    db = MagicMock(spec=Session)
    db.get.side_effect = [group, drop]
    db.scalar.return_value = uuid4()  # membership found

    token = get_squad_qr(db, group.id, User(id=uuid4()))

    claims = verify_squad_qr(token)
    assert claims["group_id"] == str(group.id)
    assert claims["drop_id"] == str(drop_id)
    assert claims["business_id"] == str(business_id)


def test_scan_squad_qr_rejects_a_different_businesss_code() -> None:
    token = sign_squad_qr(str(uuid4()), str(uuid4()), str(uuid4()))
    db = MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        scan_squad_qr(db, token, _business(uuid4()))

    assert exc_info.value.status_code == 403


def test_scan_squad_qr_requires_ready_status() -> None:
    business_id = uuid4()
    drop_id = uuid4()
    group_id = uuid4()
    token = sign_squad_qr(str(group_id), str(drop_id), str(business_id))
    group = Group(id=group_id, drop_id=drop_id, status=GroupStatus.forming)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, None]  # group lookup, existing-redemption lookup (none)

    with pytest.raises(HTTPException) as exc_info:
        scan_squad_qr(db, token, _business(business_id))

    assert exc_info.value.status_code == 409


def test_scan_squad_qr_auto_confirms(monkeypatch) -> None:
    """A staff scan is the whole verification + confirmation step — no
    further business approval gate."""
    business_id = uuid4()
    drop_id = uuid4()
    group_id = uuid4()
    token = sign_squad_qr(str(group_id), str(drop_id), str(business_id))
    group = Group(id=group_id, drop_id=drop_id, status=GroupStatus.ready)
    db = MagicMock(spec=Session)
    # group lookup, existing-redemption lookup (none), joined_member_count's own scalar
    db.scalar.side_effect = [group, None, 3]

    redemption, is_fresh = scan_squad_qr(db, token, _business(business_id))

    assert redemption.status == RedemptionStatus.confirmed
    assert redemption.business_id == business_id
    assert redemption.confirmed_by == business_id
    assert redemption.participant_count == 3
    assert group.status == GroupStatus.completed
    assert is_fresh is True
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_scan_squad_qr_is_idempotent_for_an_already_confirmed_squad() -> None:
    """Not just idempotent in what it returns — the caller uses is_fresh to
    skip re-notifying the squad too (see api/v1/redemptions.py's scan
    route), so this must come back False on a rescan, not just truthy data."""
    business_id = uuid4()
    drop_id = uuid4()
    group_id = uuid4()
    token = sign_squad_qr(str(group_id), str(drop_id), str(business_id))
    group = Group(id=group_id, drop_id=drop_id, status=GroupStatus.completed)
    existing = Redemption(id=uuid4(), status=RedemptionStatus.confirmed)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, existing]

    result, is_fresh = scan_squad_qr(db, token, _business(business_id))

    assert result is existing
    assert is_fresh is False
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
