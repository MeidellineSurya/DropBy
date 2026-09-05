"""Redemption/gamification module — XP, badges, progression.

This is the ONLY module that writes User.xp_total / User.level / UserStats.
xp = drops.xp_reward_base * rarity_multiplier (e.g. common=1x ... legendary=5x).
"""

RARITY_XP_MULTIPLIER = {
    "common": 1,
    "uncommon": 1.5,
    "rare": 2,
    "epic": 3,
    "legendary": 5,
}


def award_xp_for_redemption(redemption_id: str) -> None:
    """Insert a UserXpTransaction per Group member, update xp_total/level,
    evaluate Badge.criteria_config against updated UserStats, insert any new
    UserBadge rows, then enqueue push notifications."""
    raise NotImplementedError
