"""Redemption/gamification module — XP, badges, progression.

This is the ONLY module that writes User.xp_total / User.level / UserStats.
xp = drops.xp_reward_base * rarity_multiplier (e.g. common=1x ... legendary=5x),
plus a squad bonus when the Drop was completed as a group.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from geoalchemy2 import Geometry
from redis.exceptions import RedisError
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.businesses import Business
from app.models.drops import Drop, DropCategory, DropRarity, DropViewEvent, DropViewStage
from app.models.gamification import (
    Badge,
    BadgeCriteriaType,
    PerkType,
    PowerupType,
    UserBadge,
    UserExploredCell,
    UserPerk,
    UserPowerup,
    UserStats,
    UserXpTransaction,
    WeeklyChallengeClaim,
    XpReason,
)
from app.models.groups import Group, GroupMember, GroupMemberRole, GroupMemberStatus, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.models.users import User
from app.schemas.gamification import (
    BadgeResponse,
    DropHistoryEntry,
    PerkResponse,
    PowerupResponse,
    UserStatsResponse,
    WeeklyChallengeResponse,
)
from app.services.squad_state import (
    extend_group_capacity,
    extend_group_recruiting_window,
    group_snapshot,
)

RARITY_XP_MULTIPLIER: dict[str, float] = {
    DropRarity.common.value: 1,
    DropRarity.uncommon.value: 1.5,
    DropRarity.rare.value: 2,
    DropRarity.epic.value: 3,
    DropRarity.legendary.value: 5,
}

# A completed squad Drop earns every member a bonus on top of their base XP —
# mirrors the product brief's "+250 XP / +80 XP squad bonus" example (~30%).
SQUAD_BONUS_RATE = 0.3
XP_PER_LEVEL = 500

# Powerups are earned probabilistically from completing Rare+ Drops — a Rare
# does NOT guarantee one, unlike badges/XP which are deterministic.
POWERUP_CHANCE_BY_RARITY: dict[str, float] = {
    DropRarity.common.value: 0.0,
    DropRarity.uncommon.value: 0.0,
    DropRarity.rare.value: 0.5,
    DropRarity.epic.value: 0.75,
    DropRarity.legendary.value: 1.0,
}
LEGENDARY_BONUS_POWERUP_CHANCE = 0.2  # occasional 2nd powerup, legendary only
POWERUP_TYPES = [
    PowerupType.extra_time,
    PowerupType.xp_boost,
    PowerupType.bigger_reveal,
    PowerupType.double_or_nothing,
    PowerupType.extra_slot,
    PowerupType.streak_shield,
]

POWERUP_EXTRA_TIME_MINUTES = 5
XP_BOOST_MULTIPLIER = 1.5
REVEAL_BOOST_MULTIPLIER = 1.5
REVEAL_BOOST_MINUTES = 15
DOUBLE_OR_NOTHING_MINUTES = 15
EXTRA_SLOT_COUNT = 1

# Every 5 levels, a pending perk choice becomes available (see
# pending_perk_choices below — how many are owed is derived, not stored).
MILESTONE_LEVEL_INTERVAL = 5
BASE_POWERUP_CAP = 3
EXTRA_POWERUP_SLOT_BONUS = 1
RADIUS_PERK_BONUS_PCT = 0.15
SPECIALIZATION_PERK_BONUS_PCT = 0.05

# Purely additive: a longer streak only ever adds XP, and breaking a streak
# never removes anything you already have — see _apply_streak below.
STREAK_BONUS_PCT_PER_DAY = 0.01
STREAK_BONUS_CAP_PCT = 0.10

# Time-of-day specialization perk. There's nowhere in the schema to store a
# user's timezone, so local hour is approximated from their last known
# longitude (already captured from location pings) at 15 degrees/hour of
# solar time — not a real timezone-boundary/DST lookup, but far closer to
# their actual local time than raw UTC, and needs no new field or dependency.
TIME_SPECIALIZATION_BONUS_PCT = 0.05
NIGHT_WINDOW_LOCAL_HOURS = (21, 2)  # 9pm-2am, wraps past midnight
MORNING_WINDOW_LOCAL_HOURS = (5, 9)  # 5am-9am

# "Catch one of every rarity in a category" — a harder badge than the others,
# so a bigger bonus than the usual 1-2% is earned, not given away for free.
RARITY_SET_BADGE_BONUS_PCT = 0.08

# New-territory bonus: flat, one-time-per-cell, decoupled from rarity since
# no Drop is involved — rewards moving somewhere new, not catching anything.
TERRITORY_BONUS_XP = 10

# Weekly rotating challenge: same target/reward for everyone, category
# rotates automatically by ISO week number — nothing to schedule or roll.
WEEKLY_CHALLENGE_TARGET = 3
WEEKLY_CHALLENGE_BONUS_XP = 50
WEEKLY_CHALLENGE_CATEGORIES = list(DropCategory)


def xp_for_rarity(base: int, rarity: DropRarity | str) -> int:
    rarity_key = rarity.value if isinstance(rarity, DropRarity) else rarity
    return round(base * RARITY_XP_MULTIPLIER[rarity_key])


def squad_bonus_for(base_xp: int, member_count: int) -> int:
    return round(base_xp * SQUAD_BONUS_RATE) if member_count > 1 else 0


def level_for_xp(xp_total: int) -> int:
    return xp_total // XP_PER_LEVEL + 1


def pending_perk_choices_count(level: int, perks_taken: int) -> int:
    """How many milestone perk choices a user has earned but not yet made."""
    return max(0, level // MILESTONE_LEVEL_INTERVAL - perks_taken)


def powerup_cap(extra_slot_perks: int) -> int:
    return BASE_POWERUP_CAP + EXTRA_POWERUP_SLOT_BONUS * extra_slot_perks


def specialization_bonus_pct(perks: list[UserPerk], category: str) -> float:
    return sum(
        SPECIALIZATION_PERK_BONUS_PCT
        for perk in perks
        if perk.type == PerkType.category_specialization and perk.category == category
    )


def _hour_in_window(hour: int, window: tuple[int, int]) -> bool:
    start, end = window
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end  # wraps past midnight, e.g. (21, 2)


def time_bucket_for_hour(hour: int) -> str | None:
    """Approximate-local hour (see local_hour_for) -> "night" | "morning" | None."""
    if _hour_in_window(hour, NIGHT_WINDOW_LOCAL_HOURS):
        return "night"
    if _hour_in_window(hour, MORNING_WINDOW_LOCAL_HOURS):
        return "morning"
    return None


def approximate_utc_offset_hours(longitude: float) -> int:
    """15 degrees of longitude per hour of solar time, rounded to a whole
    hour — a real timezone follows political borders and DST, not this, but
    it needs no new field or dependency and beats treating everyone as UTC."""
    return round(longitude / 15)


def local_hour_for(utc_dt: datetime, longitude: float | None) -> int:
    """utc_dt's hour, shifted by the longitude-approximated offset. Falls
    back to the raw UTC hour if the user has no known location yet."""
    if longitude is None:
        return utc_dt.hour
    return (utc_dt.hour + approximate_utc_offset_hours(longitude)) % 24


def time_specialization_bonus_pct(perks: list[UserPerk], time_bucket: str | None) -> float:
    if time_bucket is None:
        return 0.0
    return sum(
        TIME_SPECIALIZATION_BONUS_PCT
        for perk in perks
        if perk.type == PerkType.time_specialization and perk.category == time_bucket
    )


def location_cell_for(latitude: float, longitude: float) -> str:
    """Coarse ~1.1km grid cell — shared with app/services/proximity.py's
    new-territory check so both sides agree on what counts as 'the same place'."""
    return f"{round(latitude, 2)}:{round(longitude, 2)}"


def week_key_for(today: date) -> str:
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def current_challenge_category(today: date) -> DropCategory:
    """Deterministic rotation by ISO week number — every user sees the same
    category for the same week with nothing to schedule or roll."""
    _, iso_week, _ = today.isocalendar()
    return WEEKLY_CHALLENGE_CATEGORIES[iso_week % len(WEEKLY_CHALLENGE_CATEGORIES)]


def roll_powerup_count(
    rarity: DropRarity | str, rng: Callable[[], float] = random.random
) -> int:
    """0, 1, or (rarely, legendary-only) 2. rng is injectable for tests."""
    rarity_key = rarity.value if isinstance(rarity, DropRarity) else rarity
    chance = POWERUP_CHANCE_BY_RARITY.get(rarity_key, 0.0)
    count = 1 if rng() < chance else 0
    if count and rarity_key == DropRarity.legendary.value and rng() < LEGENDARY_BONUS_POWERUP_CHANCE:
        count += 1
    return count


def roll_powerup_type(rng: Callable[[], float] = random.random) -> PowerupType:
    index = min(int(rng() * len(POWERUP_TYPES)), len(POWERUP_TYPES) - 1)
    return POWERUP_TYPES[index]


def apply_xp_boost(xp: int) -> int:
    return round(xp * XP_BOOST_MULTIPLIER)


def apply_double_or_nothing(xp: int, made_it: bool) -> int:
    return xp * 2 if made_it else 0


def streak_bonus_pct(current_streak: int) -> float:
    return min(STREAK_BONUS_CAP_PCT, max(0, current_streak - 1) * STREAK_BONUS_PCT_PER_DAY)


def badge_xp_bonus_pct(held_badges: list[Badge], category: str) -> float:
    """Sum of every held badge's passive bonus that applies to this Drop's
    category — badges with xp_bonus_category=None apply to every category."""
    return sum(
        badge.xp_bonus_pct
        for badge in held_badges
        if badge.xp_bonus_pct and (badge.xp_bonus_category is None or badge.xp_bonus_category == category)
    )


def badge_is_satisfied(badge: Badge, stats: dict) -> bool:
    """stats keys: total_drops_completed, rarity_counts, category_counts,
    cities_explored (dict), squad_leader_count, category_rarity_sets."""
    cfg = badge.criteria_config or {}
    if badge.criteria_type == BadgeCriteriaType.drop_count:
        return stats["total_drops_completed"] >= cfg.get("count", 1)
    if badge.criteria_type == BadgeCriteriaType.rarity_collected:
        return stats["rarity_counts"].get(cfg.get("rarity"), 0) >= cfg.get("count", 1)
    if badge.criteria_type == BadgeCriteriaType.category_explored:
        return stats["category_counts"].get(cfg.get("category"), 0) >= cfg.get("count", 1)
    if badge.criteria_type == BadgeCriteriaType.city_progress:
        return len(stats["cities_explored"]) >= cfg.get("count", 1)
    if badge.criteria_type == BadgeCriteriaType.squad_leader_count:
        return stats["squad_leader_count"] >= cfg.get("count", 1)
    if badge.criteria_type == BadgeCriteriaType.rarity_set_per_category:
        held = set(stats["category_rarity_sets"].get(cfg.get("category"), []))
        return set(cfg.get("rarities", [])) <= held
    return False


@dataclass
class RedemptionAwardResult:
    redemption_id: str
    group_id: str
    xp_awarded: dict[str, int] = field(default_factory=dict)
    badges_unlocked: dict[str, list[Badge]] = field(default_factory=dict)
    powerups_granted: dict[str, list[PowerupType]] = field(default_factory=dict)


def _drop_lat_lng(db: Session, drop_id: UUID) -> tuple[float, float]:
    geom = cast(Drop.location, Geometry(geometry_type="POINT", srid=4326))
    row = db.execute(
        select(func.ST_Y(geom), func.ST_X(geom)).where(Drop.id == drop_id)
    ).one()
    return float(row[0]), float(row[1])


def _user_longitude(db: Session, user_id: UUID) -> float | None:
    geom = cast(User.last_location, Geometry(geometry_type="POINT", srid=4326))
    return db.scalar(
        select(func.ST_X(geom)).where(User.id == user_id, User.last_location.isnot(None))
    )


def _squad_leader_count(db: Session, user_id: UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .join(Group, Group.id == GroupMember.group_id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.role == GroupMemberRole.leader,
            Group.status == GroupStatus.completed,
        )
    )
    return int(count or 0)


def _apply_streak(db: Session, user_id: UUID, stats: UserStats, today: date) -> None:
    """Never punishes: the worst case is current_streak resets to 1, never
    lower, and nothing else in the account is ever taken away for a gap.
    Allowed gap is 1 day by default, +1 per streak_grace perk held. A held,
    unused streak_shield powerup is auto-consumed to preserve (not grow) the
    streak through a gap that exceeds even that."""
    if stats.last_redemption_date == today:
        stats.longest_streak = max(stats.longest_streak, stats.current_streak)
        return  # a second member's redemption today doesn't double-count the streak

    grace_days = 1 + int(
        db.scalar(
            select(func.count())
            .select_from(UserPerk)
            .where(UserPerk.user_id == user_id, UserPerk.type == PerkType.streak_grace)
        )
        or 0
    )
    gap = (today - stats.last_redemption_date).days if stats.last_redemption_date else None

    if gap is not None and gap <= grace_days:
        stats.current_streak += 1
    else:
        shield = db.scalar(
            select(UserPowerup)
            .where(
                UserPowerup.user_id == user_id,
                UserPowerup.type == PowerupType.streak_shield,
                UserPowerup.used_at.is_(None),
            )
            .order_by(UserPowerup.created_at)
            .with_for_update()
        )
        if shield is not None:
            shield.used_at = datetime.now(timezone.utc)
        else:
            stats.current_streak = 1

    stats.last_redemption_date = today
    stats.longest_streak = max(stats.longest_streak, stats.current_streak)


def award_xp_for_redemption(db: Session, redemption_id: UUID) -> RedemptionAwardResult:
    """Insert a UserXpTransaction per Group member, update xp_total/level,
    evaluate Badge.criteria_config against updated UserStats, insert any new
    UserBadge rows. Idempotent: replaying an already-awarded redemption is a
    no-op that returns the previously awarded amounts."""
    redemption = db.get(Redemption, redemption_id)
    if redemption is None:
        raise ValueError("redemption not found")
    if redemption.status != RedemptionStatus.confirmed:
        raise ValueError("redemption is not confirmed")

    already_awarded = list(
        db.scalars(
            select(UserXpTransaction).where(
                UserXpTransaction.related_redemption_id == redemption.id
            )
        ).all()
    )
    if already_awarded:
        return RedemptionAwardResult(
            redemption_id=str(redemption.id),
            group_id=str(redemption.group_id),
            xp_awarded={str(row.user_id): row.amount for row in already_awarded},
        )

    drop = db.get(Drop, redemption.drop_id)
    if drop is None:
        raise ValueError("drop not found")
    members = list(
        db.scalars(
            select(GroupMember).where(
                GroupMember.group_id == redemption.group_id,
                GroupMember.status == GroupMemberStatus.joined,
            )
        ).all()
    )
    if not members:
        return RedemptionAwardResult(
            redemption_id=str(redemption.id), group_id=str(redemption.group_id)
        )

    base_xp = xp_for_rarity(drop.xp_reward_base, drop.rarity)
    total_xp = base_xp + squad_bonus_for(base_xp, len(members))
    latitude, longitude = _drop_lat_lng(db, drop.id)
    location_cell = location_cell_for(latitude, longitude)
    today = datetime.now(timezone.utc).date()

    all_badges = list(db.scalars(select(Badge)).all())
    result = RedemptionAwardResult(redemption_id=str(redemption.id), group_id=str(redemption.group_id))

    for member in members:
        user = db.scalar(select(User).where(User.id == member.user_id).with_for_update())
        if user is None:
            continue

        # Badges/perks already held BEFORE this redemption passively boost
        # it; a badge unlocked by this very redemption applies next time.
        already_unlocked_codes = set(
            db.scalars(
                select(Badge.code)
                .join(UserBadge, UserBadge.badge_id == Badge.id)
                .where(UserBadge.user_id == user.id)
            ).all()
        )
        held_badges = [badge for badge in all_badges if badge.code in already_unlocked_codes]
        member_perks = list(db.scalars(select(UserPerk).where(UserPerk.user_id == user.id)).all())

        # Stats (including the streak) update first, since today's streak
        # bonus is part of what this very redemption pays out.
        stats = db.scalar(select(UserStats).where(UserStats.user_id == user.id).with_for_update())
        if stats is None:
            # mapped_column(default=...) only applies once SQLAlchemy flushes
            # the INSERT — a freshly-constructed instance has None for every
            # other column until then, so initialize explicitly rather than
            # mutate-in-place below against an unflushed None.
            stats = UserStats(
                user_id=user.id,
                total_drops_completed=0,
                cities_explored={},
                rarity_counts={},
                category_counts={},
                category_rarity_sets={},
                longest_streak=0,
                current_streak=0,
            )
            db.add(stats)
        stats.total_drops_completed += 1
        rarity_counts = dict(stats.rarity_counts or {})
        rarity_counts[drop.rarity.value] = rarity_counts.get(drop.rarity.value, 0) + 1
        stats.rarity_counts = rarity_counts
        category_counts = dict(stats.category_counts or {})
        category_counts[drop.category.value] = category_counts.get(drop.category.value, 0) + 1
        stats.category_counts = category_counts
        category_rarity_sets = {
            category: list(rarities) for category, rarities in (stats.category_rarity_sets or {}).items()
        }
        category_rarities = set(category_rarity_sets.get(drop.category.value, []))
        category_rarities.add(drop.rarity.value)
        category_rarity_sets[drop.category.value] = sorted(category_rarities)
        stats.category_rarity_sets = category_rarity_sets
        cities = dict(stats.cities_explored or {})
        cities[location_cell] = cities.get(location_cell, 0) + 1
        stats.cities_explored = cities
        _apply_streak(db, user.id, stats, today)

        confirmed_at = redemption.confirmed_at or datetime.now(timezone.utc)
        local_hour = local_hour_for(confirmed_at, _user_longitude(db, user.id))
        time_bucket = time_bucket_for_hour(local_hour)
        bonus_pct = (
            badge_xp_bonus_pct(held_badges, drop.category.value)
            + specialization_bonus_pct(member_perks, drop.category.value)
            + time_specialization_bonus_pct(member_perks, time_bucket)
            + streak_bonus_pct(stats.current_streak)
        )
        member_xp = round(total_xp * (1 + bonus_pct))

        active_powerups = list(
            db.scalars(
                select(UserPowerup).where(
                    UserPowerup.user_id == user.id,
                    UserPowerup.used_on_group_id == redemption.group_id,
                    UserPowerup.used_at.isnot(None),
                    UserPowerup.type.in_([PowerupType.xp_boost, PowerupType.double_or_nothing]),
                )
            ).all()
        )
        for powerup in active_powerups:
            if powerup.type == PowerupType.xp_boost:
                member_xp = apply_xp_boost(member_xp)
            elif powerup.type == PowerupType.double_or_nothing:
                deadline = powerup.used_at + timedelta(minutes=DOUBLE_OR_NOTHING_MINUTES)
                made_it = (
                    redemption.checked_in_at is not None and redemption.checked_in_at <= deadline
                )
                member_xp = apply_double_or_nothing(member_xp, made_it)

        db.add(
            UserXpTransaction(
                user_id=user.id,
                amount=member_xp,
                reason=XpReason.drop_completed,
                related_redemption_id=redemption.id,
            )
        )
        user.xp_total += member_xp
        user.level = level_for_xp(user.xp_total)

        stats_snapshot = {
            "total_drops_completed": stats.total_drops_completed,
            "rarity_counts": rarity_counts,
            "category_counts": category_counts,
            "cities_explored": cities,
            "category_rarity_sets": category_rarity_sets,
            "squad_leader_count": _squad_leader_count(db, user.id),
        }
        newly_unlocked: list[Badge] = []
        for badge in all_badges:
            if badge.code in already_unlocked_codes:
                continue
            if badge_is_satisfied(badge, stats_snapshot):
                db.add(UserBadge(user_id=user.id, badge_id=badge.id))
                newly_unlocked.append(badge)

        result.xp_awarded[str(user.id)] = member_xp
        if newly_unlocked:
            result.badges_unlocked[str(user.id)] = newly_unlocked

        rolled_count = roll_powerup_count(drop.rarity)
        if rolled_count:
            extra_slot_perks = sum(
                1 for perk in member_perks if perk.type == PerkType.extra_powerup_slot
            )
            cap = powerup_cap(extra_slot_perks)
            unused_count = int(
                db.scalar(
                    select(func.count())
                    .select_from(UserPowerup)
                    .where(UserPowerup.user_id == user.id, UserPowerup.used_at.is_(None))
                )
                or 0
            )
            room = max(0, cap - unused_count)
            granted_types = [roll_powerup_type() for _ in range(min(rolled_count, room))]
            for powerup_type in granted_types:
                db.add(
                    UserPowerup(
                        user_id=user.id,
                        type=powerup_type,
                        granted_from_redemption_id=redemption.id,
                    )
                )
            if granted_types:
                result.powerups_granted[str(user.id)] = granted_types

    db.commit()
    return result


def get_user_stats(db: Session, user: User) -> UserStatsResponse:
    """User stats API: drop history, exploration progress, badges (locked and
    unlocked, so the client can render a full collection)."""
    stats = db.get(UserStats, user.id)
    unlocked_rows = db.execute(
        select(Badge, UserBadge.unlocked_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user.id)
    ).all()
    unlocked_by_code = {badge.code: unlocked_at for badge, unlocked_at in unlocked_rows}
    all_badges = list(db.scalars(select(Badge).order_by(Badge.code)).all())
    unused_powerups = list(
        db.scalars(
            select(UserPowerup)
            .where(UserPowerup.user_id == user.id, UserPowerup.used_at.is_(None))
            .order_by(UserPowerup.created_at)
        ).all()
    )
    perks = list(
        db.scalars(
            select(UserPerk).where(UserPerk.user_id == user.id).order_by(UserPerk.milestone_level)
        ).all()
    )
    extra_slot_perks = sum(1 for perk in perks if perk.type == PerkType.extra_powerup_slot)
    territory_cells_explored = int(
        db.scalar(
            select(func.count()).select_from(UserExploredCell).where(UserExploredCell.user_id == user.id)
        )
        or 0
    )

    return UserStatsResponse(
        user_id=str(user.id),
        xp_total=user.xp_total,
        level=user.level,
        xp_into_level=user.xp_total % XP_PER_LEVEL,
        xp_per_level=XP_PER_LEVEL,
        total_drops_completed=stats.total_drops_completed if stats else 0,
        rarity_counts=dict(stats.rarity_counts or {}) if stats else {},
        category_counts=dict(stats.category_counts or {}) if stats else {},
        category_rarity_sets=dict(stats.category_rarity_sets or {}) if stats else {},
        locations_explored=len(stats.cities_explored) if stats and stats.cities_explored else 0,
        territory_cells_explored=territory_cells_explored,
        current_streak=stats.current_streak if stats else 0,
        longest_streak=stats.longest_streak if stats else 0,
        badges=[
            BadgeResponse(
                code=badge.code,
                name=badge.name,
                description=badge.description,
                icon_url=badge.icon_url,
                criteria_type=badge.criteria_type,
                unlocked=badge.code in unlocked_by_code,
                unlocked_at=unlocked_by_code.get(badge.code),
            )
            for badge in all_badges
        ],
        powerups=[
            PowerupResponse(id=powerup.id, type=powerup.type) for powerup in unused_powerups
        ],
        powerup_cap=powerup_cap(extra_slot_perks),
        pending_perk_choices=pending_perk_choices_count(user.level, len(perks)),
        perks=[
            PerkResponse(milestone_level=perk.milestone_level, type=perk.type, category=perk.category)
            for perk in perks
        ],
    )


def get_drop_history(db: Session, user: User, limit: int = 100) -> list[DropHistoryEntry]:
    """Every Drop this user has completed, most recent first. Sourced from
    UserXpTransaction rows tagged drop_completed (the only reason that sets
    related_redemption_id) joined out to the Redemption/Drop/Business they
    belong to — badge/streak/specialization bonuses are folded into that same
    per-drop amount rather than being separate line items, so this list is
    exactly "drops completed," not a raw XP ledger."""
    rows = db.execute(
        select(UserXpTransaction, Redemption, Drop, Business)
        .join(Redemption, Redemption.id == UserXpTransaction.related_redemption_id)
        .join(Drop, Drop.id == Redemption.drop_id)
        .join(Business, Business.id == Redemption.business_id)
        .where(
            UserXpTransaction.user_id == user.id,
            UserXpTransaction.reason == XpReason.drop_completed,
        )
        .order_by(UserXpTransaction.created_at.desc())
        .limit(limit)
    ).all()
    return [
        DropHistoryEntry(
            redemption_id=str(redemption.id),
            drop_id=str(drop.id),
            drop_title=drop.title,
            business_name=business.name,
            category=drop.category,
            rarity=drop.rarity,
            xp_awarded=txn.amount,
            participant_count=redemption.participant_count,
            confirmed_at=redemption.confirmed_at,
        )
        for txn, redemption, drop, business in rows
    ]


async def redeem_powerup(
    db: Session, user: User, powerup_id: UUID, group_id: UUID | None
) -> tuple[PowerupType, dict]:
    """Applies a powerup's effect and marks it used. Returns (type, effect
    details) for the API layer to shape into a response. Raises HTTPException
    on invalid/already-used powerups or a missing required group_id."""
    powerup = db.scalar(
        select(UserPowerup).where(UserPowerup.id == powerup_id, UserPowerup.user_id == user.id).with_for_update()
    )
    if powerup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Powerup not found")
    if powerup.used_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This powerup has already been used")
    if powerup.type == PowerupType.streak_shield:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "streak_shield can't be redeemed manually — it's auto-consumed the moment it's needed",
        )

    now = datetime.now(timezone.utc)
    details: dict = {}

    if powerup.type == PowerupType.extra_time:
        if group_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "group_id is required")
        group = extend_group_recruiting_window(db, group_id, user, POWERUP_EXTRA_TIME_MINUTES)
        powerup.used_on_group_id = group.id
        details["group"] = group_snapshot(db, group)

    elif powerup.type == PowerupType.extra_slot:
        if group_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "group_id is required")
        group = extend_group_capacity(db, group_id, user, EXTRA_SLOT_COUNT)
        powerup.used_on_group_id = group.id
        details["group"] = group_snapshot(db, group)

    elif powerup.type in (PowerupType.xp_boost, PowerupType.double_or_nothing):
        if group_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "group_id is required")
        member = db.scalar(
            select(GroupMember.id).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user.id,
                GroupMember.status == GroupMemberStatus.joined,
            )
        )
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this squad")
        powerup.used_on_group_id = group_id
        if powerup.type == PowerupType.double_or_nothing:
            details["deadline"] = now + timedelta(minutes=DOUBLE_OR_NOTHING_MINUTES)

    elif powerup.type == PowerupType.bigger_reveal:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis_client.setex(
                f"reveal_boost:{user.id}", REVEAL_BOOST_MINUTES * 60, str(REVEAL_BOOST_MULTIPLIER)
            )
            details["boost_expires_at"] = now + timedelta(minutes=REVEAL_BOOST_MINUTES)
        except (RedisError, OSError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Could not activate boost, try again"
            ) from exc
        finally:
            await redis_client.aclose()

    powerup.used_at = now
    db.commit()
    return powerup.type, details


def choose_perk(
    db: Session, user: User, perk_type: PerkType, category: str | None
) -> UserPerk:
    """Spends one pending level-milestone perk choice. bigger_radius applies
    immediately and permanently (app/services/proximity.py reads it on the
    next location ping); extra_powerup_slot raises the cap read by
    award_xp_for_redemption above; category_specialization and
    time_specialization each require a category ("night"/"morning" for the
    latter) and stack with repeat picks of the same one."""
    if perk_type == PerkType.category_specialization and not category:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "category is required for category_specialization"
        )
    if perk_type == PerkType.time_specialization and category not in ("night", "morning"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 'category must be "night" or "morning" for time_specialization'
        )

    taken = db.scalar(
        select(func.count()).select_from(UserPerk).where(UserPerk.user_id == user.id)
    )
    pending = pending_perk_choices_count(user.level, int(taken or 0))
    if pending <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "No pending perk choices available")

    milestone_level = (int(taken or 0) + 1) * MILESTONE_LEVEL_INTERVAL
    keeps_category = perk_type in (PerkType.category_specialization, PerkType.time_specialization)
    perk = UserPerk(
        user_id=user.id,
        milestone_level=milestone_level,
        type=perk_type,
        category=category if keeps_category else None,
    )
    db.add(perk)
    db.commit()
    db.refresh(perk)
    return perk


def award_territory_bonus(user: User) -> int:
    """Flat XP for a genuinely new grid cell — see
    app/models/gamification.py::UserExploredCell and
    app/services/proximity.py, which does the insert-and-check-if-new and
    calls this. Does not commit; the caller (a discovery-engine ping) owns
    the transaction, matching the low-level-mutation/caller-commits pattern
    used elsewhere (e.g. drop_lifecycle.reserve_capacity)."""
    user.xp_total += TERRITORY_BONUS_XP
    user.level = level_for_xp(user.xp_total)
    return TERRITORY_BONUS_XP


def get_weekly_challenge_status(db: Session, user: User) -> WeeklyChallengeResponse:
    today = datetime.now(timezone.utc).date()
    category = current_challenge_category(today)
    week_key = week_key_for(today)
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)

    progress = db.scalar(
        select(func.count(func.distinct(DropViewEvent.drop_id)))
        .select_from(DropViewEvent)
        .join(Drop, Drop.id == DropViewEvent.drop_id)
        .where(
            DropViewEvent.user_id == user.id,
            DropViewEvent.stage == DropViewStage.discover,  # the "Reveal" stage — see DropViewStage's own comment
            Drop.category == category,
            DropViewEvent.created_at >= week_start_dt,
        )
    )
    claim = db.get(WeeklyChallengeClaim, {"user_id": user.id, "week_key": week_key})
    return WeeklyChallengeResponse(
        week_key=week_key,
        category=category,
        target=WEEKLY_CHALLENGE_TARGET,
        progress=min(WEEKLY_CHALLENGE_TARGET, int(progress or 0)),
        bonus_xp=WEEKLY_CHALLENGE_BONUS_XP,
        claimed=claim is not None,
    )


def claim_weekly_challenge(db: Session, user: User) -> WeeklyChallengeResponse:
    status_now = get_weekly_challenge_status(db, user)
    if status_now.claimed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This week's challenge is already claimed")
    if status_now.progress < status_now.target:
        raise HTTPException(status.HTTP_409_CONFLICT, "This week's challenge isn't complete yet")

    db.add(
        WeeklyChallengeClaim(
            user_id=user.id,
            week_key=status_now.week_key,
            category=status_now.category.value,
            xp_awarded=status_now.bonus_xp,
        )
    )
    user_row = db.scalar(select(User).where(User.id == user.id).with_for_update())
    user_row.xp_total += status_now.bonus_xp
    user_row.level = level_for_xp(user_row.xp_total)
    db.commit()
    return get_weekly_challenge_status(db, user_row)
