"""Redemption module — venue QR + check-in/confirm flow.

The QR is venue-facing and per-Drop (not per-user): one HMAC-signed token
{drop_id, business_id, iat, nonce} generated once at Drop activation and
displayed/printed by the business for the Drop's whole lifetime.

Flow:
  1. A squad member scans the venue QR -> verify(token) -> a Redemption row
     is created (status=checked_in) and the Group moves ready -> checked_in,
     pushed to the rest of the squad and to ws:business:{business_id}.
  2. Business staff tap Confirm (optionally correcting headcount) ->
     Redemption/Group -> confirmed/completed, and services.gamification
     awards XP to each member. Or Reject, if the checked-in squad turns out
     not to be legitimate — this releases the capacity it had reserved.

Redemption.participant_count is a record-keeping figure only; it does not
adjust Drop.reserved_count, which was already locked in atomically when the
squad reached "ready" (see drop_lifecycle.reserve_capacity). Reconciling a
headcount mismatch back into reserved_count is a deliberately deferred
follow-up, not something this flow needs to work.
"""

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.groups import Group, GroupMember, GroupMemberStatus, GroupStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.services.drop_lifecycle import release_capacity
from app.services.gamification import award_xp_for_redemption


def sign_venue_qr(drop_id: str, business_id: str) -> str:
    nonce = uuid.uuid4().hex
    iat = str(int(time.time()))
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    signature = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}:{signature}"


def verify_venue_qr(token: str) -> dict:
    drop_id, business_id, iat, nonce, signature = token.split(":")
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    expected = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid QR signature")
    return {"drop_id": drop_id, "business_id": business_id}


def _joined_member_ids(db: Session, group_id: UUID) -> list[UUID]:
    return list(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id,
                GroupMember.status == GroupMemberStatus.joined,
            )
        ).all()
    )


def check_in_group(db: Session, group_id: UUID, qr_token: str, user_id: UUID) -> Redemption:
    """Verify the QR, ensure it matches the Group's Drop, and ensure the
    calling user is actually a joined member of this squad — not just anyone
    who happened to see the venue's QR — before transitioning ready ->
    checked_in. Idempotent: re-scanning an already-checked-in squad just
    returns the existing Redemption rather than erroring."""
    payload = verify_venue_qr(qr_token)
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise ValueError("Squad not found")
    if str(group.drop_id) != payload["drop_id"]:
        raise ValueError("This QR is for a different Drop")
    is_member = db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    if is_member is None:
        raise ValueError("You are not a member of this squad")

    existing = db.scalar(select(Redemption).where(Redemption.group_id == group_id))
    if existing is not None:
        return existing

    if group.status != GroupStatus.ready:
        raise ValueError("This squad is not ready to check in")

    now = datetime.now(timezone.utc)
    redemption = Redemption(
        drop_id=group.drop_id,
        group_id=group.id,
        business_id=UUID(payload["business_id"]),
        status=RedemptionStatus.checked_in,
        checked_in_at=now,
    )
    db.add(redemption)
    group.status = GroupStatus.checked_in
    group.checked_in_at = now
    db.commit()
    db.refresh(redemption)
    return redemption


def confirm_redemption(
    db: Session,
    redemption_id: UUID,
    business_id: UUID,
    confirmed_by_business_id: UUID,
    participant_count: int | None = None,
) -> tuple[Redemption, dict[str, int]]:
    """Complete the Group and award XP. Returns (redemption, xp_awarded) so
    the route can broadcast both in one redemption.confirmed event."""
    redemption = db.scalar(
        select(Redemption)
        .where(Redemption.id == redemption_id, Redemption.business_id == business_id)
        .with_for_update()
    )
    if redemption is None:
        raise ValueError("Redemption not found")
    if redemption.status != RedemptionStatus.checked_in:
        raise ValueError("This redemption is not awaiting confirmation")
    group = db.get(Group, redemption.group_id)
    if group is None:
        raise ValueError("Squad no longer exists")

    now = datetime.now(timezone.utc)
    member_ids = _joined_member_ids(db, group.id)
    actual_count = participant_count if participant_count is not None else len(member_ids)
    redemption.status = RedemptionStatus.confirmed
    redemption.confirmed_at = now
    redemption.confirmed_by = confirmed_by_business_id
    redemption.participant_count = actual_count
    group.status = GroupStatus.completed
    group.completed_at = now

    xp_awarded = award_xp_for_redemption(db, redemption, member_ids)
    db.commit()
    db.refresh(redemption)
    return redemption, xp_awarded


def reject_redemption(db: Session, redemption_id: UUID, business_id: UUID) -> Redemption:
    """The business declines a checked-in squad (e.g. the people who showed
    up don't match the squad on record). Releases the capacity the squad had
    reserved so a legitimate squad can use it instead."""
    redemption = db.scalar(
        select(Redemption)
        .where(Redemption.id == redemption_id, Redemption.business_id == business_id)
        .with_for_update()
    )
    if redemption is None:
        raise ValueError("Redemption not found")
    if redemption.status != RedemptionStatus.checked_in:
        raise ValueError("This redemption is not awaiting confirmation")
    group = db.get(Group, redemption.group_id)

    redemption.status = RedemptionStatus.rejected
    if group is not None:
        member_count = db.scalar(
            select(func.count())
            .select_from(GroupMember)
            .where(
                GroupMember.group_id == group.id,
                GroupMember.status == GroupMemberStatus.joined,
            )
        )
        group.status = GroupStatus.cancelled
        release_capacity(db, group.drop_id, member_count or 0)
    db.commit()
    db.refresh(redemption)
    return redemption
