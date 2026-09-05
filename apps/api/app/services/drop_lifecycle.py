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
    description: str | None = None,
    interest_tag: str | None = None,
    rarity: DropRarity = DropRarity.common,
    min_group_size: int = 1,
    max_group_size: int = 1,
    discovery_radius_m: int = settings.default_detect_radius_m,
    reveal_radius_m: int = settings.default_reveal_radius_m,
    discover_radius_m: int = settings.default_discover_radius_m,
    xp_reward_base: int = 10,
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
    if xp_reward_base < 0:
        raise ValueError("xp_reward_base cannot be negative")

    now = datetime.now(timezone.utc)
    lifecycle_status = DropStatus.draft
    if publish:
        lifecycle_status = (
            DropStatus.scheduled if starts_at > now else DropStatus.active
        )

    drop = Drop(
        business_id=business_id,
        title=clean_title,
        description=description,
        category=category,
        interest_tag=clean_interest_tag,
        rarity=rarity,
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
        xp_reward_base=xp_reward_base,
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
    """Temporarily hide an active Drop from discovery without cancelling it or
    releasing its reserved capacity; forming/ready squads are left alone."""
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
