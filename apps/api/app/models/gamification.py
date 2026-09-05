import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class XpReason(str, enum.Enum):
    drop_completed = "drop_completed"
    badge_unlocked = "badge_unlocked"
    bonus = "bonus"


class BadgeCriteriaType(str, enum.Enum):
    drop_count = "drop_count"
    rarity_collected = "rarity_collected"
    category_explored = "category_explored"
    city_progress = "city_progress"
    squad_leader_count = "squad_leader_count"
    rarity_set_per_category = "rarity_set_per_category"  # one of every rarity tier within one category


class PowerupType(str, enum.Enum):
    extra_time = "extra_time"  # extends a still-forming squad's recruiting window
    xp_boost = "xp_boost"  # 1.5x XP on the redemption it's tagged to
    bigger_reveal = "bigger_reveal"  # temporary +50% Reveal radius
    double_or_nothing = "double_or_nothing"  # 2x XP if checked in within 15 min, else 0
    extra_slot = "extra_slot"  # lets one more person join a forming/ready squad
    streak_shield = "streak_shield"  # auto-consumed to save a streak that would otherwise reset


class UserXpTransaction(Base):
    __tablename__ = "user_xp_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[XpReason] = mapped_column(Enum(XpReason))
    related_redemption_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String, nullable=True)
    criteria_type: Mapped[BadgeCriteriaType] = mapped_column(Enum(BadgeCriteriaType))
    criteria_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    # A small passive XP bonus for having this badge unlocked, applied on top
    # of every future redemption. xp_bonus_category=None applies to every
    # Drop; set it to scope the bonus to one category (e.g. "food_dining").
    # Kept modest for today's milestone-style badges — a harder, rarer future
    # badge (e.g. a full-area completionist) is where a bigger number belongs.
    xp_bonus_pct: Mapped[float] = mapped_column(Float, default=0.0)
    xp_bonus_category: Mapped[str | None] = mapped_column(String, nullable=True)


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    badge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badges.id"), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPowerup(Base):
    """Earned probabilistically from completing Rare+ Drops (see
    services/gamification.py::roll_powerup_count). Redeeming one calls into
    app/services/squad_state.py::extend_group_recruiting_window."""

    __tablename__ = "user_powerups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[PowerupType] = mapped_column(Enum(PowerupType), default=PowerupType.extra_time)
    granted_from_redemption_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_on_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PerkType(str, enum.Enum):
    bigger_radius = "bigger_radius"  # permanent +15%/pick Reveal radius, stacks with the bigger_reveal powerup
    extra_powerup_slot = "extra_powerup_slot"  # +1/pick to the unused-powerup inventory cap
    category_specialization = "category_specialization"  # +5%/pick XP for one chosen category, stacks per category
    streak_grace = "streak_grace"  # +1 day/pick of allowed gap before a streak resets
    time_specialization = "time_specialization"  # +5%/pick XP for one chosen time-of-day window ("night"/"morning")


class UserPerk(Base):
    """One choice made at a level milestone (every 5 levels — see
    services/gamification.py::MILESTONE_LEVEL_INTERVAL). How many are
    available is derived (user.level // 5 minus rows here), not stored."""

    __tablename__ = "user_perks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    milestone_level: Mapped[int] = mapped_column(Integer)
    type: Mapped[PerkType] = mapped_column(Enum(PerkType))
    # A generic specialization key: a Drop category for category_specialization,
    # or "night"/"morning" for time_specialization. Unused otherwise.
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserExploredCell(Base):
    """One row per coarse lat/lng grid cell (see UserStats.cities_explored's
    comment) a user's location ping has ever landed in — independent of any
    Drop. Feeds the "new territory" flat XP bonus in
    services/gamification.py::award_territory_bonus, applied the moment a
    genuinely new cell is inserted (see services/proximity.py)."""

    __tablename__ = "user_explored_cells"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    cell: Mapped[str] = mapped_column(String, primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeeklyChallengeClaim(Base):
    """One row per user per claimed week. week_key is an ISO week string
    (e.g. "2026-W36") from services/gamification.py::week_key_for — its
    existence is the only thing preventing re-claiming the same week."""

    __tablename__ = "weekly_challenge_claims"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    week_key: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserStats(Base):
    """Denormalized rollup, owned by app/services/gamification.py."""

    __tablename__ = "user_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    total_drops_completed: Mapped[int] = mapped_column(Integer, default=0)
    # Keyed by a coarse "lat:lng" grid cell (2-decimal rounding, ~1.1km) since
    # there is no city/region model yet — a defensible proxy for exploration
    # spread without inventing geo-boundary data the schema doesn't have.
    cities_explored: Mapped[dict] = mapped_column(JSONB, default=dict)
    rarity_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    category_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {category: [distinct rarities completed in it]} — feeds the
    # rarity_set_per_category "catch one of every rarity" badge.
    category_rarity_sets: Mapped[dict] = mapped_column(JSONB, default=dict)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_redemption_date: Mapped[date | None] = mapped_column(Date, nullable=True)
