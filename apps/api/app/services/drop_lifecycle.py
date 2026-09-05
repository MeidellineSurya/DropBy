"""Drop lifecycle and atomic participant-capacity accounting."""

from datetime import datetime, timezone
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.drops import (
    Drop,
    DropCategory,
    DropRarity,
    DropStatus,
    DropType,
)
from app.models.groups import Group, GroupStatus

# Richest-first: the first threshold discount_percent clears wins.
_DISCOUNT_TIER_THRESHOLDS: list[tuple[int, DropRarity]] = [
    (80, DropRarity.legendary),
    (60, DropRarity.epic),
    (40, DropRarity.rare),
    (20, DropRarity.uncommon),
    (0, DropRarity.common),
]
_RARITY_ORDER = [
    DropRarity.common,
    DropRarity.uncommon,
    DropRarity.rare,
    DropRarity.epic,
    DropRarity.legendary,
]
# A Drop this scarce (few total spots) or this demanding (a large required
# group) reads as more special than its discount alone suggests — matching
# the brief's own language ("Epic: very limited", "Legendary: extremely rare").
_SCARCITY_CAPACITY_MAX = 6
_COMMITMENT_GROUP_MIN = 6


def compute_rarity(
    discount_percent: int, min_group_size: int, max_capacity_participants: int
) -> DropRarity:
    """Rarity is never business-declared (see api/v1/business_drops.py — the
    create schema has no rarity field at all) — it's derived here from the
    offer's actual terms, so a business can't just label a 5%-off coffee
    upgrade "Legendary". This is the only place that produces a rarity value;
    keep it that way rather than accepting an override anywhere upstream.
    """
    tier = next(
        rarity
        for threshold, rarity in _DISCOUNT_TIER_THRESHOLDS
        if discount_percent >= threshold
    )
    is_scarce_or_demanding = (
        max_capacity_participants <= _SCARCITY_CAPACITY_MAX
        or min_group_size >= _COMMITMENT_GROUP_MIN
    )
    if is_scarce_or_demanding:
        bumped_index = min(_RARITY_ORDER.index(tier) + 1, len(_RARITY_ORDER) - 1)
        tier = _RARITY_ORDER[bumped_index]
    return tier


# Same reasoning as rarity: XP was a business-set field with nothing behind
# it either, so a business could pair a 5%-off Drop with a 10,000-XP reward.
# Doubling per tier keeps "rarer = more reward" an honest, fixed relationship.
_XP_REWARD_BY_RARITY: dict[DropRarity, int] = {
    DropRarity.common: 10,
    DropRarity.uncommon: 20,
    DropRarity.rare: 40,
    DropRarity.epic: 80,
    DropRarity.legendary: 160,
}


def compute_xp_reward(rarity: DropRarity) -> int:
    """The only place that produces an xp_reward_base value — see
    compute_rarity's docstring; the same "never business-declared" rule
    applies here. Always called with a rarity compute_rarity() itself
    produced, never a value from user input."""
    return _XP_REWARD_BY_RARITY[rarity]


def create_drop(
    db: Session,
    *,
    business_id: UUID,
    title: str,
    category: DropCategory,
    drop_type: DropType,
    latitude: float,
    longitude: float,
    max_capacity_participants: int,
    starts_at: datetime,
    ends_at: datetime,
    discount_percent: int,
    description: str | None = None,
    interest_tag: str | None = None,
    min_group_size: int = 1,
    max_group_size: int = 1,
    discovery_radius_m: int = settings.default_detect_radius_m,
    reveal_radius_m: int = settings.default_reveal_radius_m,
    discover_radius_m: int = settings.default_discover_radius_m,
    publish: bool = False,
) -> Drop:
    """Validate and stage a new Drop inside the caller's transaction.

    The business module owns its public route and authentication; it calls this
    boundary so lifecycle status and invariants keep a single writer.
    """
    clean_title = title.strip()
    clean_interest_tag = (interest_tag or category.value).strip().lower()
    if not clean_title:
        raise ValueError("title is required")
    if not clean_interest_tag:
        raise ValueError("interest_tag is required")
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise ValueError("starts_at and ends_at must include a timezone")
    if ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")
    if publish and ends_at <= datetime.now(timezone.utc):
        raise ValueError("an expired Drop cannot be published")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("invalid latitude or longitude")
    if not 0 < discover_radius_m <= reveal_radius_m <= discovery_radius_m:
        raise ValueError("radii must satisfy 0 < close Reveal <= legacy radius <= Detect")
    if min_group_size < 1 or max_group_size < min_group_size:
        raise ValueError("invalid group-size range")
    if drop_type == DropType.solo and (min_group_size != 1 or max_group_size != 1):
        raise ValueError("solo Drops must use a group size of 1")
    if max_capacity_participants < min_group_size:
        raise ValueError("capacity must fit at least one minimum-size group")
    if not 1 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 1 and 100")

    now = datetime.now(timezone.utc)
    lifecycle_status = DropStatus.draft
    if publish:
        lifecycle_status = (
            DropStatus.scheduled if starts_at > now else DropStatus.active
        )

    rarity = compute_rarity(discount_percent, min_group_size, max_capacity_participants)
    drop = Drop(
        business_id=business_id,
        title=clean_title,
        description=description,
        category=category,
        interest_tag=clean_interest_tag,
        rarity=rarity,
        discount_percent=discount_percent,
        drop_type=drop_type,
        min_group_size=min_group_size,
        max_group_size=max_group_size,
        location=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
        discovery_radius_m=discovery_radius_m,
        reveal_radius_m=reveal_radius_m,
        discover_radius_m=discover_radius_m,
        max_capacity_participants=max_capacity_participants,
        starts_at=starts_at,
        ends_at=ends_at,
        xp_reward_base=compute_xp_reward(rarity),
        status=lifecycle_status,
        reserved_count=0,
    )
    db.add(drop)
    db.flush()
    return drop


def publish_drop(db: Session, drop_id: UUID, business_id: UUID) -> Drop | None:
    """Move a business's own draft Drop live, using the same scheduled-vs-active
    staging rule as create_drop(..., publish=True)."""
    drop = db.scalar(
        select(Drop)
        .where(Drop.id == drop_id, Drop.business_id == business_id)
        .with_for_update()
    )
    if drop is None or drop.status != DropStatus.draft:
        return None
    now = datetime.now(timezone.utc)
    if drop.ends_at <= now:
        raise ValueError("an expired Drop cannot be published")
    drop.status = DropStatus.scheduled if drop.starts_at > now else DropStatus.active
    db.commit()
    return drop


def pause_drop(db: Session, drop_id: UUID, business_id: UUID) -> Drop | None:
    """Temporarily hide an active Drop from new discovery (proximity queries
    only ever return status == active) without cancelling it or releasing its
    reserved capacity. Existing forming/ready squads are usually left alone,
    but reserve_capacity() only reserves against an active Drop — a squad
    that crosses its min_required in the same instant this pauses will lose
    that race and be cancelled rather than admitted. See
    describe_capacity_failure(), used by services/squad_state.py, for why
    that cancellation is reported to members as "paused", not "sold out"."""
    changed = db.execute(
        update(Drop)
        .where(
            Drop.id == drop_id,
            Drop.business_id == business_id,
            Drop.status == DropStatus.active,
        )
        .values(status=DropStatus.paused)
    ).rowcount
    if not changed:
        return None
    db.commit()
    return db.get(Drop, drop_id)


def resume_drop(db: Session, drop_id: UUID, business_id: UUID) -> Drop | None:
    changed = db.execute(
        update(Drop)
        .where(
            Drop.id == drop_id,
            Drop.business_id == business_id,
            Drop.status == DropStatus.paused,
            Drop.ends_at > func.now(),
        )
        .values(status=DropStatus.active)
    ).rowcount
    if not changed:
        return None
    db.commit()
    return db.get(Drop, drop_id)


def activate_drop(db: Session, drop_id: UUID) -> Drop | None:
    drop = db.scalar(select(Drop).where(Drop.id == drop_id).with_for_update())
    if drop is None or drop.status != DropStatus.scheduled:
        return None
    now = datetime.now(timezone.utc)
    if drop.starts_at > now or drop.ends_at <= now:
        return None
    drop.status = DropStatus.active
    db.flush()
    return drop


def reserve_capacity(db: Session, drop_id: UUID, count: int) -> int | None:
    """Reserve capacity with one conditional UPDATE; returns the new total."""
    if count <= 0:
        raise ValueError("count must be positive")
    reserved = db.scalar(
        update(Drop)
        .where(
            Drop.id == drop_id,
            Drop.status == DropStatus.active,
            Drop.ends_at > func.now(),
            Drop.reserved_count + count <= Drop.max_capacity_participants,
        )
        .values(reserved_count=Drop.reserved_count + count)
        .returning(Drop.reserved_count)
    )
    if reserved is not None:
        db.execute(
            update(Drop)
            .where(
                Drop.id == drop_id,
                Drop.reserved_count >= Drop.max_capacity_participants,
            )
            .values(status=DropStatus.capacity_reached)
        )
    return reserved


def describe_capacity_failure(db: Session, drop_id: UUID) -> str:
    """A human-readable reason for a reserve_capacity(...) -> None result,
    for user-facing messages only — this never gates a decision itself (that
    stays atomic in reserve_capacity). The Drop's row can still change
    between the failed reservation and this read; worst case a caller shows
    a slightly stale explanation, never incorrect capacity data."""
    drop = db.get(Drop, drop_id)
    if drop is None:
        return "This Drop no longer exists."
    if drop.ends_at <= datetime.now(timezone.utc):
        return "This Drop has ended."
    if drop.status == DropStatus.paused:
        return "This Drop is temporarily paused by the business."
    if drop.status != DropStatus.active:
        return "This Drop is no longer active."
    return "This Drop has reached full capacity."


def release_capacity(db: Session, drop_id: UUID, count: int) -> None:
    if count <= 0:
        raise ValueError("count must be positive")
    db.execute(
        update(Drop)
        .where(Drop.id == drop_id)
        .values(reserved_count=func.greatest(0, Drop.reserved_count - count))
    )
    db.execute(
        update(Drop)
        .where(
            Drop.id == drop_id,
            Drop.status == DropStatus.capacity_reached,
            Drop.ends_at > func.now(),
        )
        .values(status=DropStatus.active)
    )


def cancel_drop(
    db: Session, drop_id: UUID, business_id: UUID | None = None
) -> list[UUID] | None:
    """`business_id` scopes cancellation to a business's own Drop when provided
    (the business-facing route always passes it); left optional so an eventual
    admin/moderation caller can cancel across businesses.

    Returns None if the Drop couldn't be cancelled (not found, not owned, or
    already in a terminal state), otherwise the ids of any forming/ready
    Groups that were cascaded to cancelled — callers use this list to notify
    affected squads (see api/v1/business_drops.py)."""
    conditions = [
        Drop.id == drop_id,
        Drop.status.not_in(
            [DropStatus.completed, DropStatus.cancelled, DropStatus.expired]
        ),
    ]
    if business_id is not None:
        conditions.append(Drop.business_id == business_id)
    changed = db.execute(
        update(Drop).where(*conditions).values(status=DropStatus.cancelled)
    ).rowcount
    if not changed:
        return None
    group_ids = list(
        db.scalars(
            update(Group)
            .where(
                Group.drop_id == drop_id,
                Group.status.in_([GroupStatus.forming, GroupStatus.ready]),
            )
            .values(status=GroupStatus.cancelled)
            .returning(Group.id)
        ).all()
    )
    db.commit()
    return group_ids


def activate_scheduled(db: Session) -> list[UUID]:
    ids = list(
        db.scalars(
            update(Drop)
            .where(
                Drop.status == DropStatus.scheduled,
                Drop.starts_at <= func.now(),
                Drop.ends_at > func.now(),
            )
            .values(status=DropStatus.active)
            .returning(Drop.id)
        ).all()
    )
    db.commit()
    return ids


def expire_due(db: Session) -> tuple[list[UUID], list[UUID]]:
    drop_ids = list(
        db.scalars(
            update(Drop)
            .where(
                Drop.status.in_(
                    [
                        DropStatus.scheduled,
                        DropStatus.active,
                        DropStatus.paused,
                        DropStatus.capacity_reached,
                    ]
                ),
                Drop.ends_at <= func.now(),
            )
            .values(status=DropStatus.expired)
            .returning(Drop.id)
        ).all()
    )
    group_ids: list[UUID] = []
    if drop_ids:
        group_ids = list(
            db.scalars(
                update(Group)
                .where(
                    Group.drop_id.in_(drop_ids),
                    Group.status.in_([GroupStatus.forming, GroupStatus.ready]),
                )
                .values(status=GroupStatus.expired)
                .returning(Group.id)
            ).all()
        )
    db.commit()
    return drop_ids, group_ids
