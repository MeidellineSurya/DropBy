"""Redemption module — a per-squad QR the business scans to confirm.

The business is the one that verifies and confirms a claim — not a location
claim the consumer self-reports (that was tried; see STATUS.md's "Dropping
the venue QR for a location claim" and "Auto-confirm plus a dispute window"
for why it wasn't enough on its own — no human ever looked at a redemption
before a reward was granted, and GPS alone is spoofable).

The QR now belongs to the *squad*, not the venue: once a Group reaches
"ready", any member can pull up a signed, per-squad code in the app and show
it to staff. Staff scan it (on the business dashboard, or eventually a
business-side mobile scanner) — that scan itself both verifies the squad is
genuinely standing in front of a business representative and confirms the
redemption, in one action. No separate business "Confirm" tap needed after
the fact, and no GPS check needed either: a staff member physically scanning
a code held up by the squad is a stronger presence signal than either.

Flow:
  1. Group reaches "ready" (app/services/squad_state.py) — capacity reserved.
  2. Any member calls GET /groups/{id}/qr -> get_squad_qr() returns a signed,
     self-verifying token ({group_id, drop_id, business_id, iat, nonce}).
     Stateless and re-fetchable any number of times without invalidating an
     already-displayed code, same as the old venue QR.
  3. Staff scan it on the dashboard -> POST /redemptions/scan ->
     scan_squad_qr() verifies the signature and that it's this business's
     own Drop, transitions the Group straight to completed / Redemption
     straight to confirmed, and the caller enqueues award_xp_for_redemption,
     whose Celery task publishes redemption.confirmed over ws:group:{id} and
     ws:user:{id} for every member, plus a push notification.
  4. Business staff can instead flag a confirmed redemption as fraudulent or
     mistaken within DISPUTE_WINDOW -> dispute_redemption() -> records-only:
     releases capacity, does NOT claw back XP already awarded. A proper
     clawback would also need to unwind any badges/streaks/stats that
     redemption already contributed to, which isn't built.
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
from app.services.drop_lifecycle import release_capacity

# How long after confirmation a business can still dispute a redemption.
DISPUTE_WINDOW = timedelta(hours=24)


def sign_squad_qr(group_id: str, drop_id: str, business_id: str) -> str:
    nonce = uuid.uuid4().hex
    iat = str(int(time.time()))
    message = f"{group_id}:{drop_id}:{business_id}:{iat}:{nonce}"
    signature = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}:{signature}"


def verify_squad_qr(token: str) -> dict:
    try:
        group_id, drop_id, business_id, iat, nonce, signature = token.split(":")
    except ValueError as exc:
        raise ValueError("malformed QR token") from exc
    message = f"{group_id}:{drop_id}:{business_id}:{iat}:{nonce}"
    expected = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid QR signature")
    return {"group_id": group_id, "drop_id": drop_id, "business_id": business_id}


def joined_member_count(db: Session, group_id: UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .where(GroupMember.group_id == group_id, GroupMember.status == GroupMemberStatus.joined)
    )
    return int(count or 0)


def get_squad_qr(db: Session, group_id: UUID, user: User) -> str:
    """A squad member pulls up their squad's check-in code. Re-fetchable any
    number of times — it's stateless, so nothing to invalidate."""
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    member = db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    if member is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this squad")
    if group.status != GroupStatus.ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Squad is not ready to check in (status={group.status.value})",
        )
    drop = db.get(Drop, group.drop_id)
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
    return sign_squad_qr(str(group.id), str(drop.id), str(drop.business_id))


def scan_squad_qr(db: Session, qr_token: str, business: Business) -> Redemption:
    """Business staff scan a squad's code — this both verifies and confirms
    the redemption in one action. There is no further approval step."""
    try:
        claims = verify_squad_qr(qr_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if claims["business_id"] != str(business.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This code belongs to a different business")

    group_id = UUID(claims["group_id"])
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Squad not found")
    if str(group.drop_id) != claims["drop_id"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "This code is for a different Drop")

    existing = db.scalar(select(Redemption).where(Redemption.group_id == group.id))
    if existing is not None and existing.status == RedemptionStatus.confirmed:
        return existing  # idempotent rescan
    if group.status != GroupStatus.ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Squad is not ready to check in (status={group.status.value})",
        )

    now = datetime.now(timezone.utc)
    member_count = joined_member_count(db, group.id)
    if existing is None:
        existing = Redemption(
            drop_id=group.drop_id,
            group_id=group.id,
            business_id=business.id,
            status=RedemptionStatus.confirmed,
            checked_in_at=now,
            confirmed_at=now,
            confirmed_by=business.id,
            participant_count=member_count,
        )
        db.add(existing)
    else:
        existing.status = RedemptionStatus.confirmed
        existing.checked_in_at = existing.checked_in_at or now
        existing.confirmed_at = now
        existing.confirmed_by = business.id
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
