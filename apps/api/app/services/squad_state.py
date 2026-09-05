"""Squad state machine and capacity-safe ready transition."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.drops import Drop, DropStatus, DropViewEvent, DropViewStage
from app.models.groups import (
    Group,
    GroupMember,
    GroupMemberRole,
    GroupMemberStatus,
    GroupStatus,
)
from app.models.users import User
from app.schemas.groups import GroupMemberResponse, GroupResponse
from app.services.drop_lifecycle import reserve_capacity

ACTIVE_GROUP_STATES = [GroupStatus.forming, GroupStatus.ready, GroupStatus.checked_in]


def group_snapshot(db: Session, group: Group) -> GroupResponse:
    rows = db.execute(
        select(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .where(
            GroupMember.group_id == group.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
        .order_by(GroupMember.joined_at)
    ).all()
    return GroupResponse(
        id=str(group.id),
        drop_id=str(group.drop_id),
        created_by_user_id=str(group.created_by_user_id),
        status=group.status,
        current_count=len(rows),
        min_required=group.min_required,
        max_allowed=group.max_allowed,
        open_to_nearby=group.open_to_nearby,
        expires_at=group.expires_at,
        members=[
            GroupMemberResponse(
                user_id=str(member.user_id),
                display_name=user.display_name,
                role=member.role,
                status=member.status,
            )
            for member, user in rows
        ],
    )


def create_group(
    db: Session, drop_id: UUID, user: User, open_to_nearby: bool
) -> GroupResponse:
    drop = db.scalar(select(Drop).where(Drop.id == drop_id).with_for_update())
    if (
        drop is None
        or drop.status != DropStatus.active
        or drop.ends_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active Drop not found")
    revealed = db.scalar(
        select(DropViewEvent.id).where(
            DropViewEvent.user_id == user.id,
            DropViewEvent.drop_id == drop_id,
            DropViewEvent.stage == DropViewStage.discover,
        )
    )
    if revealed is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Reveal this Drop before creating a squad"
        )
    if _active_group_for_user(db, user.id, drop_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You already have a squad for this Drop"
        )

    group = Group(
        drop_id=drop.id,
        created_by_user_id=user.id,
        min_required=drop.min_group_size,
        max_allowed=drop.max_group_size,
        open_to_nearby=open_to_nearby,
        expires_at=drop.ends_at,
    )
    db.add(group)
    db.flush()
    db.add(
        GroupMember(
            group_id=group.id,
            user_id=user.id,
            role=GroupMemberRole.leader,
            status=GroupMemberStatus.joined,
            joined_at=datetime.now(timezone.utc),
        )
    )
    db.flush()
    if group.min_required == 1:
        if reserve_capacity(db, drop.id, 1) is None:
            group.status = GroupStatus.cancelled
        else:
            group.status = GroupStatus.ready
            group.ready_at = datetime.now(timezone.utc)
    db.commit()
    return group_snapshot(db, group)


def join_group(
    db: Session, group_id: UUID, user: User
) -> tuple[GroupResponse, bool, bool]:
    """Join a forming/ready squad.

    Returns (snapshot, member_added, became_ready). Ready squads remain open
    until max_allowed so their count can progress 2/4 -> 3/4 -> 4/4.
    """
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    if group.status not in (GroupStatus.forming, GroupStatus.ready) or (
        group.expires_at and group.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Squad can no longer be joined")
    if not group.open_to_nearby:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Squad is invite-only")
    if not _user_can_assemble(db, user, group.drop_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Reveal this Drop and stay nearby before joining a squad",
        )

    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id, GroupMember.user_id == user.id
        )
    )
    if member and member.status == GroupMemberStatus.joined:
        return group_snapshot(db, group), False, False
    if _active_group_for_user(db, user.id, group.drop_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You already have a squad for this Drop"
        )

    count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .where(
            GroupMember.group_id == group.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    count = int(count or 0)
    if count >= group.max_allowed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Squad is full")
    if member:
        member.status = GroupMemberStatus.joined
        member.joined_at = datetime.now(timezone.utc)
    else:
        db.add(
            GroupMember(
                group_id=group.id,
                user_id=user.id,
                role=GroupMemberRole.member,
                status=GroupMemberStatus.joined,
                joined_at=datetime.now(timezone.utc),
            )
        )
    new_count = count + 1
    became_ready = (
        group.status == GroupStatus.forming and new_count >= group.min_required
    )
    if became_ready:
        if reserve_capacity(db, group.drop_id, new_count) is None:
            group.status = GroupStatus.cancelled
        else:
            group.status = GroupStatus.ready
            group.ready_at = datetime.now(timezone.utc)
    elif (
        group.status == GroupStatus.ready
        and reserve_capacity(db, group.drop_id, 1) is None
    ):
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Drop capacity is full")
    db.commit()
    return (
        group_snapshot(db, group),
        True,
        became_ready and group.status == GroupStatus.ready,
    )


def leave_group(db: Session, group_id: UUID, user: User) -> GroupResponse | None:
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    if group.status != GroupStatus.forming:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A ready squad can no longer be left"
        )
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not in this squad")
    member.status = GroupMemberStatus.left
    remaining = list(
        db.scalars(
            select(GroupMember)
            .where(
                GroupMember.group_id == group.id,
                GroupMember.user_id != user.id,
                GroupMember.status == GroupMemberStatus.joined,
            )
            .order_by(GroupMember.joined_at)
        ).all()
    )
    if not remaining:
        group.status = GroupStatus.cancelled
        db.commit()
        return None
    if group.created_by_user_id == user.id:
        new_leader = remaining[0]
        group.created_by_user_id = new_leader.user_id
        new_leader.role = GroupMemberRole.leader
    db.commit()
    return group_snapshot(db, group)


def get_group_for_member(db: Session, group_id: UUID, user_id: UUID) -> GroupResponse:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    member = db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user_id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this squad")
    return group_snapshot(db, group)


def _active_group_for_user(db: Session, user_id: UUID, drop_id: UUID) -> bool:
    return bool(
        db.scalar(
            select(GroupMember.id)
            .join(Group, Group.id == GroupMember.group_id)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.status == GroupMemberStatus.joined,
                Group.drop_id == drop_id,
                Group.status.in_(ACTIVE_GROUP_STATES),
            )
        )
    )


def _user_can_assemble(db: Session, user: User, drop_id: UUID) -> bool:
    if (
        user.last_location is None
        or user.last_location_at is None
        or user.last_location_at < datetime.now(timezone.utc) - timedelta(minutes=5)
    ):
        return False
    revealed = db.scalar(
        select(DropViewEvent.id).where(
            DropViewEvent.user_id == user.id,
            DropViewEvent.drop_id == drop_id,
            DropViewEvent.stage == DropViewStage.discover,
        )
    )
    if revealed is None:
        return False
    return bool(
        db.scalar(
            select(
                func.ST_DWithin(
                    Drop.location, User.last_location, Drop.discover_radius_m
                )
            )
            .select_from(Drop)
            .join(User, User.id == user.id)
            .where(Drop.id == drop_id)
        )
    )
