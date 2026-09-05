"""Redemption/gamification module — XP, badges, progression.

This is the ONLY module that writes User.xp_total / User.level / UserStats.

xp = drops.xp_reward_base — and nothing else. xp_reward_base is already
rarity-scaled at Drop creation time (see
services/drop_lifecycle.compute_xp_reward, keyed off compute_rarity), so
award it as-is per member; do not re-apply a rarity multiplier here or XP
gets double-scaled for every tier above common.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.drops import Drop
from app.models.redemption import Redemption
from app.models.users import User


def award_xp_for_redemption(
    db: Session, redemption: Redemption, member_ids: list[UUID]
) -> dict[str, int]:
    """Grants each squad member drops.xp_reward_base for this Drop.

    This is the minimal slice of the originally-planned flow: no
    UserXpTransaction ledger rows, no UserStats rollup, no badge evaluation,
    and no leveling formula (User.level is untouched) — those tables exist
    but aren't migrated, and are a separate, larger follow-up, not required
    for a member to actually receive XP.

    Returns {user_id: xp_awarded} for the caller to broadcast in a
    redemption.confirmed WS event. Caller commits; this only stages the
    UPDATE so it lands in the same transaction as the redemption/group
    status change.
    """
    if not member_ids:
        return {}
    xp_reward = db.scalar(select(Drop.xp_reward_base).where(Drop.id == redemption.drop_id))
    if xp_reward is None:
        return {}
    db.execute(
        update(User).where(User.id.in_(member_ids)).values(xp_total=User.xp_total + xp_reward)
    )
    return {str(user_id): xp_reward for user_id in member_ids}
