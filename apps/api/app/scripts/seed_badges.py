"""Seed default Badge definitions so gamification criteria have something to
unlock. Idempotent: safe to re-run (matches on Badge.code).

xp_bonus_pct/xp_bonus_category: a small passive XP bonus for having the badge
unlocked (see app/models/gamification.py::Badge). Kept modest (1-2%) for
these milestone-style badges; a future, much harder badge (e.g. a full-area
completionist) is where a bigger number would belong.
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.drops import DropCategory, DropRarity
from app.models.gamification import Badge, BadgeCriteriaType
from app.services.gamification import RARITY_SET_BADGE_BONUS_PCT

DEFAULT_BADGES = [
    {
        "code": "first_drop",
        "name": "First Catch",
        "description": "Complete your first Drop.",
        "criteria_type": BadgeCriteriaType.drop_count,
        "criteria_config": {"count": 1},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
    {
        "code": "drop_veteran",
        "name": "Drop Veteran",
        "description": "Complete 10 Drops.",
        "criteria_type": BadgeCriteriaType.drop_count,
        "criteria_config": {"count": 10},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
    {
        "code": "rare_hunter",
        "name": "Rare Hunter",
        "description": "Complete 3 Rare Drops.",
        "criteria_type": BadgeCriteriaType.rarity_collected,
        "criteria_config": {"rarity": "rare", "count": 3},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
    {
        "code": "legendary_collector",
        "name": "Legendary Collector",
        "description": "Complete a Legendary Drop.",
        "criteria_type": BadgeCriteriaType.rarity_collected,
        "criteria_config": {"rarity": "legendary", "count": 1},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
    {
        "code": "foodie",
        "name": "Foodie",
        "description": "Complete 5 food & dining Drops.",
        "criteria_type": BadgeCriteriaType.category_explored,
        "criteria_config": {"category": "food_dining", "count": 5},
        "xp_bonus_pct": 0.02,
        "xp_bonus_category": "food_dining",
    },
    {
        "code": "night_owl",
        "name": "Night Owl",
        "description": "Complete 3 nightlife Drops.",
        "criteria_type": BadgeCriteriaType.category_explored,
        "criteria_config": {"category": "nightlife", "count": 3},
        "xp_bonus_pct": 0.02,
        "xp_bonus_category": "nightlife",
    },
    {
        "code": "city_explorer",
        "name": "City Explorer",
        "description": "Complete Drops in 5 different locations.",
        "criteria_type": BadgeCriteriaType.city_progress,
        "criteria_config": {"count": 5},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
    {
        "code": "squad_leader",
        "name": "Squad Leader",
        "description": "Lead 5 squads to a completed Drop.",
        "criteria_type": BadgeCriteriaType.squad_leader_count,
        "criteria_config": {"count": 5},
        "xp_bonus_pct": 0.01,
        "xp_bonus_category": None,
    },
]

# One "catch every rarity" set-bonus badge per category — a genuinely harder
# badge than the others above, so it earns a bigger bonus (8% vs 1-2%).
ALL_RARITIES = [rarity.value for rarity in DropRarity]
DEFAULT_BADGES += [
    {
        "code": f"set_{category.value}",
        "name": f"{category.value.replace('_', ' ').title()} Connoisseur",
        "description": (
            f"Complete a Common, Uncommon, Rare, Epic, and Legendary "
            f"{category.value.replace('_', ' ')} Drop."
        ),
        "criteria_type": BadgeCriteriaType.rarity_set_per_category,
        "criteria_config": {"category": category.value, "rarities": ALL_RARITIES},
        "xp_bonus_pct": RARITY_SET_BADGE_BONUS_PCT,
        "xp_bonus_category": category.value,
    }
    for category in DropCategory
]


def seed() -> None:
    with SessionLocal() as db:
        for definition in DEFAULT_BADGES:
            badge = db.scalar(select(Badge).where(Badge.code == definition["code"]))
            if badge is None:
                db.add(Badge(**definition))
            else:
                badge.name = definition["name"]
                badge.description = definition["description"]
                badge.criteria_type = definition["criteria_type"]
                badge.criteria_config = definition["criteria_config"]
                badge.xp_bonus_pct = definition["xp_bonus_pct"]
                badge.xp_bonus_category = definition["xp_bonus_category"]
        db.commit()
    print(f"Seeded {len(DEFAULT_BADGES)} badge definitions")


if __name__ == "__main__":
    seed()
