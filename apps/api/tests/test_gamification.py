from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.redemption import Redemption, RedemptionStatus
from app.services.gamification import award_xp_for_redemption


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


def test_award_xp_for_redemption_grants_each_member_the_drops_xp_reward() -> None:
    redemption = make_redemption()
    member_ids = [uuid4(), uuid4(), uuid4()]
    db = MagicMock(spec=Session)
    db.scalar.return_value = 40  # Drop.xp_reward_base

    result = award_xp_for_redemption(db, redemption, member_ids)

    assert result == {str(uid): 40 for uid in member_ids}
    db.execute.assert_called_once()


def test_award_xp_for_redemption_returns_empty_for_no_members() -> None:
    db = MagicMock(spec=Session)

    result = award_xp_for_redemption(db, make_redemption(), [])

    assert result == {}
    db.execute.assert_not_called()


def test_award_xp_for_redemption_handles_a_missing_drop_gracefully() -> None:
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    result = award_xp_for_redemption(db, make_redemption(), [uuid4()])

    assert result == {}
    db.execute.assert_not_called()
