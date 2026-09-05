"""Redemption/gamification module — XP, badges, progression.

This is the ONLY module that writes User.xp_total / User.level / UserStats.

xp = drops.xp_reward_base — and nothing else. xp_reward_base is already
rarity-scaled at Drop creation time (see
services/drop_lifecycle.compute_xp_reward, keyed off compute_rarity), so
award it as-is per member; do not re-apply a rarity multiplier here or XP
gets double-scaled for every tier above common.
"""


def award_xp_for_redemption(redemption_id: str) -> None:
    """Insert a UserXpTransaction per Group member, update xp_total/level,
    evaluate Badge.criteria_config against updated UserStats, insert any new
    UserBadge rows, then enqueue push notifications."""
    raise NotImplementedError
