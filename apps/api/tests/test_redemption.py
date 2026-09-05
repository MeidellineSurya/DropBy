from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.groups import Group, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.services.redemption import reject_redemption, sign_venue_qr, verify_venue_qr


def test_sign_and_verify_venue_qr_roundtrip() -> None:
    token = sign_venue_qr("drop-123", "business-456")

    claims = verify_venue_qr(token)

    assert claims == {"drop_id": "drop-123", "business_id": "business-456"}


def test_verify_venue_qr_rejects_tampered_signature() -> None:
    token = sign_venue_qr("drop-123", "business-456")
    drop_id, _business_id, iat, nonce, signature = token.split(":")
    tampered = f"{drop_id}:attacker-business:{iat}:{nonce}:{signature}"

    with pytest.raises(ValueError, match="invalid QR signature"):
        verify_venue_qr(tampered)


def test_verify_venue_qr_rejects_malformed_token() -> None:
    with pytest.raises(ValueError, match="malformed QR token"):
        verify_venue_qr("not-a-real-token")


def test_repeated_signing_produces_independently_valid_tokens() -> None:
    """Re-fetching the QR (get_venue_qr) any number of times must never
    invalidate a copy already printed/displayed by the business."""
    first = sign_venue_qr("drop-123", "business-456")
    second = sign_venue_qr("drop-123", "business-456")

    assert first != second
    assert verify_venue_qr(first) == verify_venue_qr(second)


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
    from fastapi import HTTPException

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
    from fastapi import HTTPException

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
