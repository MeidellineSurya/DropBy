"""Business-facing performance metrics.

No Redemption table exists yet (owned by the redemption/gamification
workstream), so "redemption counts" isn't literally available. Until that
lands, squad progress (forming/ready/checked_in/completed counts) is the best
available proxy for how a Drop is converting, alongside the detect->reveal
funnel already recorded by the discovery engine in drop_view_events.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.drops import Drop, DropStatus, DropViewEvent, DropViewStage
from app.models.groups import Group, GroupStatus
from app.schemas.business_analytics import BusinessOverviewResponse, DropFunnelResponse


def _funnel_counts(db: Session, drop_id: UUID) -> dict[DropViewStage, int]:
    rows = db.execute(
        select(DropViewEvent.stage, func.count(func.distinct(DropViewEvent.user_id)))
        .where(DropViewEvent.drop_id == drop_id)
        .group_by(DropViewEvent.stage)
    ).all()
    return {stage: count for stage, count in rows}


def _squad_counts(db: Session, drop_id: UUID) -> dict[GroupStatus, int]:
    rows = db.execute(
        select(Group.status, func.count(Group.id))
        .where(Group.drop_id == drop_id)
        .group_by(Group.status)
    ).all()
    return {status: count for status, count in rows}


def drop_funnel(db: Session, drop: Drop) -> DropFunnelResponse:
    funnel = _funnel_counts(db, drop.id)
    squads = _squad_counts(db, drop.id)
    return DropFunnelResponse(
        drop_id=str(drop.id),
        status=drop.status,
        detect_count=funnel.get(DropViewStage.detect, 0),
        revealed_count=funnel.get(DropViewStage.discover, 0),
        reserved_count=drop.reserved_count,
        max_capacity_participants=drop.max_capacity_participants,
        squads_forming=squads.get(GroupStatus.forming, 0),
        squads_ready=squads.get(GroupStatus.ready, 0),
        squads_checked_in=squads.get(GroupStatus.checked_in, 0),
        squads_completed=squads.get(GroupStatus.completed, 0),
    )


def business_overview(db: Session, business_id: UUID) -> BusinessOverviewResponse:
    status_counts = dict(
        db.execute(
            select(Drop.status, func.count(Drop.id))
            .where(Drop.business_id == business_id)
            .group_by(Drop.status)
        ).all()
    )
    capacity_row = db.execute(
        select(
            func.coalesce(func.sum(Drop.reserved_count), 0),
            func.coalesce(func.sum(Drop.max_capacity_participants), 0),
        ).where(
            Drop.business_id == business_id,
            Drop.status.in_([DropStatus.active, DropStatus.capacity_reached]),
        )
    ).one()
    since = datetime.now(timezone.utc) - timedelta(days=7)
    distinct_viewers = db.scalar(
        select(func.count(func.distinct(DropViewEvent.user_id)))
        .join(Drop, Drop.id == DropViewEvent.drop_id)
        .where(Drop.business_id == business_id, DropViewEvent.created_at >= since)
    )
    return BusinessOverviewResponse(
        active_drops=status_counts.get(DropStatus.active, 0),
        draft_drops=status_counts.get(DropStatus.draft, 0),
        scheduled_drops=status_counts.get(DropStatus.scheduled, 0),
        total_reserved_participants=capacity_row[0],
        total_capacity_participants=capacity_row[1],
        distinct_viewers_last_7_days=distinct_viewers or 0,
    )
