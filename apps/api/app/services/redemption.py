"""Redemption module — venue QR + check-in/confirm flow.

The QR is venue-facing and per-Drop (not per-user): one HMAC-signed token
{drop_id, business_id, iat, nonce} generated once at Drop activation and
displayed/printed by the business for the Drop's whole lifetime. The token is
self-verifying (the signature covers everything needed to check it), so
re-fetching it via get_venue_qr any number of times is safe and never
invalidates an already-printed copy.

Flow:
  1. Group reaches "ready" (app/services/squad_state.py).
  2. Any member scans the venue QR -> check_in_group() verifies the QR,
     confirms the scanning member is nearby (geofence), and transitions the
     Group/Redemption to checked_in. Pushed to the rest of the squad and to
     ws:business:{business_id}.
  3. Business staff tap Confirm (optionally correcting headcount) ->
     confirm_redemption() -> Redemption/Group -> completed, capacity
     reconciled, award_xp_for_redemption Celery task enqueued by the caller.
     Staff can instead tap Reject (a mistaken or fraudulent scan) ->
     reject_redemption() -> Redemption/Group -> rejected/cancelled, with the
     squad's reserved capacity released back to the Drop.
"""

import hashlib
import hmac
import time
import uuid
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
from app.services.drop_lifecycle import release_capacity, reserve_capacity

# A member's last location must be this fresh to check in — longer than the
# 5-minute assemble window in squad_state.py because walking to the venue
# after assembling a squad legitimately takes time.
CHECK_IN_LOCATION_FRESHNESS = timedelta(minutes=15)


def sign_venue_qr(drop_id: str, business_id: str) -> str:
    nonce = uuid.uuid4().hex
    iat = str(int(time.time()))
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    signature = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}:{signature}"


def verify_venue_qr(token: str) -> dict:
    try:
        drop_id, business_id, iat, nonce, signature = token.split(":")
    except ValueError as exc:
        raise ValueError("malformed QR token") from exc
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    expected = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid QR signature")
    return {"drop_id": drop_id, "business_id": business_id}


def get_venue_qr(db: Session, drop_id: UUID, business: Business) -> str:
    drop = db.get(Drop, drop_id)
    if drop is None or drop.business_id != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
    return sign_venue_qr(str(drop.id), str(business.id))


def _within_geofence(db: Session, user: User, drop: Drop) -> bool:
    if user.last_location is None or user.last_location_at is None:
        return False
    if user.last_location_at < datetime.now(timezone.utc) - CHECK_IN_LOCATION_FRESHNESS:
        return False
    return bool(
        db.scalar(
            select(func.ST_DWithin(Drop.location, User.last_location, Drop.discover_radius_m))
            .select_from(Drop)
            .join(User, User.id == user.id)
            .where(Drop.id == drop.id)
        )
    )


def check_in_group(
    db: Session, group_id: UUID, qr_token: str, scanning_user: User
) -> Redemption:
    """Verify the QR, ensure it matches the Group's Drop, transition to checked_in."""
    try:
        claims = verify_venue_qr(qr_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    drop_id = UUID(claims["drop_id"])
    business_id = UUID(claims["business_id"])

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
    if group.drop_id != drop_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This QR code is for a different Drop")

    existing = db.scalar(select(Redemption).where(Redemption.group_id == group.id))
    if group.status == GroupStatus.checked_in and existing is not None:
        return existing  # idempotent re-scan by another member
    if group.status != GroupStatus.ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Squad is not ready to check in (status={group.status.value})",
        )

    drop = db.get(Drop, drop_id)
    if drop is None or drop.business_id != business_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "QR code does not match this venue")
    if not _within_geofence(db, scanning_user, drop):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Move closer to the venue to check in"
        )

    now = datetime.now(timezone.utc)
    if existing is None:
        existing = Redemption(
            drop_id=drop_id,
            group_id=group.id,
            business_id=business_id,
            status=RedemptionStatus.checked_in,
            checked_in_at=now,
        )
        db.add(existing)
    else:
        existing.status = RedemptionStatus.checked_in
        existing.checked_in_at = now
    group.status = GroupStatus.checked_in
    group.checked_in_at = now
    db.commit()
    db.refresh(existing)
    return existing


def joined_member_count(db: Session, group_id: UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.status == GroupMemberStatus.joined)
    )
    return int(count or 0)


def confirm_redemption(
    db: Session,
    redemption_id: UUID,
    business: Business,
    participant_count: int | None,
) -> Redemption:
    """Complete the Group, reconcile capacity, and mark the Redemption confirmed.

    The caller enqueues award_xp_for_redemption once this returns, keeping the
    XP/badge side effects outside this transaction.
    """
    redemption = db.scalar(
        select(Redemption).where(Redemption.id == redemption_id).with_for_update()
    )
    if redemption is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Redemption not found")
    if redemption.business_id != business.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This redemption belongs to a different business"
        )
    if redemption.status == RedemptionStatus.confirmed:
        return redemption  # idempotent
    if redemption.status != RedemptionStatus.checked_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Redemption cannot be confirmed from status={redemption.status.value}",
        )

    group = db.scalar(select(Group).where(Group.id == redemption.group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")

    joined_count = joined_member_count(db, group.id)
    actual_count = participant_count if participant_count is not None else joined_count
    if actual_count < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "participant_count must be at least 1")

    # The Drop's reserved_count already reflects joined_count for this group
    # (reserved incrementally as members joined). A headcount correction only
    # needs to move the delta.
    delta = actual_count - joined_count
    if delta > 0:
        if reserve_capacity(db, group.drop_id, delta) is None:
            actual_count = joined_count  # no spare capacity: ignore the extra walk-ins
    elif delta < 0:
        release_capacity(db, group.drop_id, -delta)

    now = datetime.now(timezone.utc)
    redemption.status = RedemptionStatus.confirmed
    redemption.confirmed_at = now
    redemption.confirmed_by = business.id
    redemption.participant_count = actual_count
    group.status = GroupStatus.completed
    group.completed_at = now
    db.commit()
    db.refresh(redemption)
    return redemption


def reject_redemption(db: Session, redemption_id: UUID, business: Business) -> Redemption:
    """Business rejects a checked-in squad — a mistaken or fraudulent scan —
    instead of confirming it. Releases the squad's reserved capacity back to
    the Drop rather than leaving it stuck as checked_in forever with no way
    for anyone else to claim that spot.
    """
    redemption = db.scalar(
        select(Redemption).where(Redemption.id == redemption_id).with_for_update()
    )
    if redemption is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Redemption not found")
    if redemption.business_id != business.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This redemption belongs to a different business"
        )
    if redemption.status == RedemptionStatus.rejected:
        return redemption  # idempotent
    if redemption.status != RedemptionStatus.checked_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Redemption cannot be rejected from status={redemption.status.value}",
        )

    group = db.scalar(select(Group).where(Group.id == redemption.group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")

    member_count = joined_member_count(db, group.id)
    if member_count > 0:
        release_capacity(db, group.drop_id, member_count)

    redemption.status = RedemptionStatus.rejected
    redemption.confirmed_at = datetime.now(timezone.utc)
    redemption.confirmed_by = business.id
    group.status = GroupStatus.cancelled
    db.commit()
    db.refresh(redemption)
    return redemption


def list_redemption_queue(
    db: Session, business: Business, statuses: list[RedemptionStatus] | None = None
) -> list[Redemption]:
    """The business dashboard's live redemption queue."""
    statuses = statuses or [RedemptionStatus.checked_in]
    return list(
        db.scalars(
            select(Redemption)
            .where(Redemption.business_id == business.id, Redemption.status.in_(statuses))
            .order_by(Redemption.checked_in_at.desc().nullslast())
        ).all()
    )


def build_response(db: Session, redemption: Redemption) -> RedemptionResponse:
    """RedemptionResponse plus the Drop title/XP and current joined headcount
    the dashboard's queue cards show — none of that lives on Redemption
    itself, so it's assembled here rather than left to a bare
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
        member_count=joined_member_count(db, redemption.group_id),
        xp_reward_base=drop.xp_reward_base if drop else 0,
    )
