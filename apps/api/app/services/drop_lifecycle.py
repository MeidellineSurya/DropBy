"""Drop lifecycle and atomic participant-capacity accounting."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.drops import Drop, DropStatus
from app.models.groups import Group, GroupStatus


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


def cancel_drop(db: Session, drop_id: UUID) -> bool:
    changed = db.execute(
        update(Drop)
        .where(
            Drop.id == drop_id,
            Drop.status.not_in(
                [DropStatus.completed, DropStatus.cancelled, DropStatus.expired]
            ),
        )
        .values(status=DropStatus.cancelled)
    ).rowcount
    if not changed:
        return False
    db.execute(
        update(Group)
        .where(
            Group.drop_id == drop_id,
            Group.status.in_([GroupStatus.forming, GroupStatus.ready]),
        )
        .values(status=GroupStatus.cancelled)
    )
    db.commit()
    return True


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
