from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.drops import DropCategory, DropRarity
from app.models.gamification import BadgeCriteriaType, PerkType, PowerupType
from app.schemas.groups import GroupResponse


class BadgeResponse(BaseModel):
    code: str
    name: str
    description: str | None
    icon_url: str | None
    criteria_type: BadgeCriteriaType
    xp_bonus_pct: float
    xp_bonus_category: str | None
    unlocked: bool
    unlocked_at: datetime | None = None


class PowerupResponse(BaseModel):
    id: UUID
    type: PowerupType


class PerkResponse(BaseModel):
    milestone_level: int
    type: PerkType
    category: str | None = None


class UserStatsResponse(BaseModel):
    user_id: str
    xp_total: int
    level: int
    xp_into_level: int
    xp_per_level: int
    total_drops_completed: int
    rarity_counts: dict[str, int]
    category_counts: dict[str, int]
    category_rarity_sets: dict[str, list[str]]
    locations_explored: int
    territory_cells_explored: int
    current_streak: int
    longest_streak: int
    badges: list[BadgeResponse]
    powerups: list[PowerupResponse]
    powerup_cap: int
    pending_perk_choices: int
    perks: list[PerkResponse]


class ChoosePerkRequest(BaseModel):
    type: PerkType
    category: str | None = None  # required only for category_specialization


class RedeemPowerupRequest(BaseModel):
    # Required for extra_time, extra_slot, xp_boost, and double_or_nothing;
    # omit for bigger_reveal, which is a personal timed buff, not squad-scoped.
    group_id: UUID | None = None


class RedeemPowerupResponse(BaseModel):
    powerup_type: PowerupType
    group: GroupResponse | None = None
    deadline: datetime | None = None
    boost_expires_at: datetime | None = None


class DropHistoryEntry(BaseModel):
    redemption_id: str
    drop_id: str
    drop_title: str
    business_name: str
    category: DropCategory
    rarity: DropRarity
    xp_awarded: int
    participant_count: int | None
    confirmed_at: datetime


class WeeklyChallengeResponse(BaseModel):
    week_key: str
    category: DropCategory
    target: int
    progress: int
    bonus_xp: int
    claimed: bool
