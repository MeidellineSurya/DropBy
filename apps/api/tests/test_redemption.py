from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.groups import Group, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.services.redemption import (
    check_in_group,
    confirm_redemption,
    reject_redemption,
    sign_venue_qr,
    verify_venue_qr,
)


def make_group(**overrides) -> Group:
    defaults = dict(
        id=uuid4(),
        drop_id=uuid4(),
        created_by_user_id=uuid4(),
        status=GroupStatus.ready,
        min_required=2,
        max_allowed=4,
        open_to_nearby=True,
    )
    defaults.update(overrides)
    return Group(**defaults)


def make_redemption(**overrides) -> Redemption:
    defaults = dict(
        id=uuid4(),
        drop_id=uuid4(),
        group_id=uuid4(),
        business_id=uuid4(),
        status=RedemptionStatus.checked_in,
    )
    defaults.update(overrides)
    return Redemption(**defaults)


# --- QR sign/verify ---------------------------------------------------


def test_qr_round_trips() -> None:
    drop_id, business_id = str(uuid4()), str(uuid4())
    token = sign_venue_qr(drop_id, business_id)
    payload = verify_venue_qr(token)
    assert payload == {"drop_id": drop_id, "business_id": business_id}


def test_qr_rejects_a_tampered_signature() -> None:
    token = sign_venue_qr(str(uuid4()), str(uuid4()))
    tampered = token[:-4] + "0000"
    with pytest.raises(ValueError, match="invalid QR signature"):
        verify_venue_qr(tampered)


# --- check_in_group -----------------------------------------------------


def test_check_in_group_creates_a_redemption_and_advances_the_group() -> None:
    drop_id, business_id, user_id = uuid4(), uuid4(), uuid4()
    token = sign_venue_qr(str(drop_id), str(business_id))
    group = make_group(drop_id=drop_id, status=GroupStatus.ready)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, uuid4(), None]  # group, is_member, existing

    redemption = check_in_group(db, group.id, token, user_id)

    assert redemption.status == RedemptionStatus.checked_in
    assert redemption.business_id == business_id
    assert group.status == GroupStatus.checked_in
    assert group.checked_in_at is not None
    db.add.assert_called_once()
    db.commit.assert_called_once_with()


def test_check_in_group_is_idempotent_on_repeat_scan() -> None:
    group = make_group()
    existing = make_redemption(group_id=group.id)
    token = sign_venue_qr(str(group.drop_id), str(uuid4()))
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, uuid4(), existing]

    result = check_in_group(db, group.id, token, uuid4())

    assert result is existing
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_check_in_group_rejects_a_qr_for_a_different_drop() -> None:
    group = make_group(drop_id=uuid4())
    token = sign_venue_qr(str(uuid4()), str(uuid4()))  # different drop_id
    db = MagicMock(spec=Session)
    db.scalar.return_value = group

    with pytest.raises(ValueError, match="different Drop"):
        check_in_group(db, group.id, token, uuid4())


def test_check_in_group_rejects_a_non_member() -> None:
    group = make_group()
    token = sign_venue_qr(str(group.drop_id), str(uuid4()))
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, None]  # group found, not a member

    with pytest.raises(ValueError, match="not a member"):
        check_in_group(db, group.id, token, uuid4())


def test_check_in_group_rejects_a_squad_that_is_not_ready() -> None:
    group = make_group(status=GroupStatus.forming)
    token = sign_venue_qr(str(group.drop_id), str(uuid4()))
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [group, uuid4(), None]

    with pytest.raises(ValueError, match="not ready to check in"):
        check_in_group(db, group.id, token, uuid4())


# --- confirm_redemption ---------------------------------------------------


@patch("app.services.redemption.award_xp_for_redemption")
def test_confirm_redemption_completes_group_and_defaults_participant_count(
    mock_award: MagicMock,
) -> None:
    redemption = make_redemption()
    group = make_group(id=redemption.group_id, status=GroupStatus.checked_in)
    member_ids = [uuid4(), uuid4()]
    mock_award.return_value = {str(uid): 40 for uid in member_ids}

    db = MagicMock(spec=Session)
    db.scalar.return_value = redemption
    db.get.return_value = group
    db.scalars.return_value.all.return_value = member_ids

    result, xp_awarded = confirm_redemption(
        db, redemption.id, redemption.business_id, redemption.business_id
    )

    assert result.status == RedemptionStatus.confirmed
    assert result.participant_count == len(member_ids)
    assert group.status == GroupStatus.completed
    assert xp_awarded == mock_award.return_value
    mock_award.assert_called_once_with(db, redemption, member_ids)
    db.commit.assert_called_once_with()


@patch("app.services.redemption.award_xp_for_redemption", return_value={})
def test_confirm_redemption_honors_an_explicit_participant_count(_: MagicMock) -> None:
    redemption = make_redemption()
    group = make_group(id=redemption.group_id, status=GroupStatus.checked_in)
    db = MagicMock(spec=Session)
    db.scalar.return_value = redemption
    db.get.return_value = group
    db.scalars.return_value.all.return_value = [uuid4(), uuid4()]

    result, _xp = confirm_redemption(
        db, redemption.id, redemption.business_id, redemption.business_id, participant_count=5
    )

    assert result.participant_count == 5


def test_confirm_redemption_rejects_a_redemption_not_awaiting_confirmation() -> None:
    redemption = make_redemption(status=RedemptionStatus.confirmed)
    db = MagicMock(spec=Session)
    db.scalar.return_value = redemption

    with pytest.raises(ValueError, match="not awaiting confirmation"):
        confirm_redemption(db, redemption.id, redemption.business_id, redemption.business_id)


def test_confirm_redemption_raises_when_not_found() -> None:
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    with pytest.raises(ValueError, match="not found"):
        confirm_redemption(db, uuid4(), uuid4(), uuid4())


# --- reject_redemption ---------------------------------------------------


def test_reject_redemption_cancels_group_and_releases_capacity() -> None:
    redemption = make_redemption()
    group = make_group(id=redemption.group_id, status=GroupStatus.checked_in)
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [redemption, 3]  # redemption, member_count
    db.get.return_value = group

    with patch("app.services.redemption.release_capacity") as mock_release:
        result = reject_redemption(db, redemption.id, redemption.business_id)

    assert result.status == RedemptionStatus.rejected
    assert group.status == GroupStatus.cancelled
    mock_release.assert_called_once_with(db, group.drop_id, 3)
    db.commit.assert_called_once_with()


def test_reject_redemption_rejects_a_redemption_not_awaiting_confirmation() -> None:
    redemption = make_redemption(status=RedemptionStatus.rejected)
    db = MagicMock(spec=Session)
    db.scalar.return_value = redemption

    with pytest.raises(ValueError, match="not awaiting confirmation"):
        reject_redemption(db, redemption.id, redemption.business_id)
