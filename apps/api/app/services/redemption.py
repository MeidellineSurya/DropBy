"""Redemption module — location-claim check-in, auto-confirmed on the spot.

Check-in is a location claim, not a QR scan: any squad member taps "Check in
now" in the app, the server verifies their last known location is genuinely
close to the venue (a much tighter radius than the Reveal distance — see
settings.check_in_radius_m), and the whole squad both checks in AND is
confirmed in the same step. There is no business approval gate and no
"awaiting confirm" resting state — capacity was already first-come-first-
served reserved when the squad became ready, so there is nothing left for a
human to gate at check-in time.

This trades away real-time human verification for instant reward and zero
business-side friction. The recourse that remains: a business can dispute a
confirmed redemption within DISPUTE_WINDOW as fraudulent or mistaken.
Disputing is a records-only flag — it releases the squad's reserved capacity
back to the Drop, but does NOT claw back XP already awarded. A proper
clawback would also need to unwind any badges/streaks/stats that redemption
already contributed to, which isn't built. See STATUS.md's "Auto-confirm
plus a dispute window" for the full reasoning; a printed QR or a return to a
human pre-confirm gate are both still on the table if spoofed/abusive claims
turn out to be a real problem beyond pilot scale.

Flow:
  1. Group reaches "ready" (app/services/squad_state.py) — capacity reserved.
  2. Any member taps "Check in now" -> check_in_group() confirms membership,
     confirms the group is ready, confirms the scanning member is within
     check_in_radius_m of the Drop's venue, and transitions the Group
     straight to completed / Redemption straight to confirmed. The caller
     enqueues award_xp_for_redemption, whose Celery task publishes
     redemption.confirmed over ws:group:{id} and ws:user:{id} for every
     member, plus a push notification.
  3. Business staff can instead tap "Flag as fraudulent" within
     DISPUTE_WINDOW of confirmation -> dispute_redemption() -> records-only,
     releases capacity, no XP clawback.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.businesses import Business
from app.models.drops import Drop
from app.models.groups import Group, GroupMember, GroupMemberStatus, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.models.users import User
from app.schemas.redemption import RedemptionResponse
from app.services.drop_lifecycle import release_capacity

# A member's last location must be this fresh to check in — longer than the
# 5-minute assemble window in squad_state.py because walking to the venue
# after assembling a squad legitimately takes time.
CHECK_IN_LOCATION_FRESHNESS = timedelta(minutes=15)

# How long after confirmation a business can still dispute a redemption.
DISPUTE_WINDOW = timedelta(hours=24)


def _within_check_in_range(db: Session, user: User, drop: Drop) -> bool:
    if user.last_location is None or user.last_location_at is None:
        return False
    if user.last_location_at < datetime.now(timezone.utc) - CHECK_IN_LOCATION_FRESHNESS:
        return False
    return bool(
        db.scalar(
            select(func.ST_DWithin(Drop.location, User.last_location, settings.check_in_radius_m))
            .select_from(Drop)
            .join(User, User.id == user.id)
            .where(Drop.id == drop.id)
        )
    )


def joined_member_count(db: Session, group_id: UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.status == GroupMemberStatus.joined)
    )
    return int(count or 0)


def check_in_group(db: Session, group_id: UUID, scanning_user: User) -> Redemption:
    """Confirm membership and proximity, then auto-confirm the redemption —
    there is no separate business approval step (see module docstring)."""
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == scanning_user.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this squad")

    existing = db.scalar(select(Redemption).where(Redemption.group_id == group.id))
    if existing is not None and existing.status == RedemptionStatus.confirmed:
        return existing  # idempotent repeat claim by another member
    if group.status != GroupStatus.ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Squad is not ready to check in (status={group.status.value})",
        )

    drop = db.get(Drop, group.drop_id)
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
    if not _within_check_in_range(db, scanning_user, drop):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Move closer to the venue to check in"
        )

    now = datetime.now(timezone.utc)
    member_count = joined_member_count(db, group.id)
    if existing is None:
        existing = Redemption(
            drop_id=drop.id,
            group_id=group.id,
            business_id=drop.business_id,
            status=RedemptionStatus.confirmed,
            checked_in_at=now,
            confirmed_at=now,
            confirmed_by=drop.business_id,
            participant_count=member_count,
        )
        db.add(existing)
    else:
        existing.status = RedemptionStatus.confirmed
        existing.checked_in_at = existing.checked_in_at or now
        existing.confirmed_at = now
        existing.confirmed_by = drop.business_id
        existing.participant_count = member_count
    group.status = GroupStatus.completed
    group.checked_in_at = group.checked_in_at or now
    group.completed_at = now
    db.commit()
    db.refresh(existing)
    return existing


def dispute_redemption(db: Session, redemption_id: UUID, business: Business) -> Redemption:
    """Business flags a confirmed redemption as fraudulent or mistaken,
    within DISPUTE_WINDOW of confirmation. Releases the squad's reserved
    capacity back to the Drop. Does NOT claw back XP already awarded — see
    module docstring."""
    redemption = db.scalar(
        select(Redemption).where(Redemption.id == redemption_id).with_for_update()
    )
    if redemption is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Redemption not found")
    if redemption.business_id != business.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This redemption belongs to a different business"
        )
    if redemption.disputed_at is not None:
        return redemption  # idempotent
    if redemption.status != RedemptionStatus.confirmed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a confirmed redemption can be disputed (status={redemption.status.value})",
        )
    if redemption.confirmed_at is None or (
        datetime.now(timezone.utc) - redemption.confirmed_at > DISPUTE_WINDOW
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The dispute window for this redemption has passed"
        )

    if redemption.participant_count:
        release_capacity(db, redemption.drop_id, redemption.participant_count)

    redemption.disputed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(redemption)
    return redemption


def list_recent_redemptions(db: Session, business: Business) -> list[Redemption]:
    """Confirmed redemptions still inside the dispute window — the business
    dashboard's redemptions list, disputable while shown here."""
    cutoff = datetime.now(timezone.utc) - DISPUTE_WINDOW
    return list(
        db.scalars(
            select(Redemption)
            .where(
                Redemption.business_id == business.id,
                Redemption.status == RedemptionStatus.confirmed,
                Redemption.confirmed_at >= cutoff,
            )
            .order_by(Redemption.confirmed_at.desc())
        ).all()
    )


def build_response(db: Session, redemption: Redemption) -> RedemptionResponse:
    """RedemptionResponse plus the Drop title/XP and current joined headcount
    the dashboard's list shows — none of that lives on Redemption itself, so
    it's assembled here rather than left to a bare
    RedemptionResponse.model_validate(redemption) at each call site (which
    would fail: those fields aren't attributes on the ORM model)."""
    drop = db.get(Drop, redemption.drop_id)
    return RedemptionResponse(
        id=redemption.id,
        drop_id=redemption.drop_id,
        drop_title=drop.title if drop else "(deleted Drop)",
        group_id=redemption.group_id,
        business_id=redemption.business_id,
        status=redemption.status,
        checked_in_at=redemption.checked_in_at,
        confirmed_at=redemption.confirmed_at,
        participant_count=redemption.participant_count,
        disputed_at=redemption.disputed_at,
        member_count=joined_member_count(db, redemption.group_id),
        xp_reward_base=drop.xp_reward_base if drop else 0,
    )
