from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business
from app.models.drops import Drop
from app.models.groups import GroupMember, GroupMemberStatus
from app.models.redemption import Redemption, RedemptionStatus
from app.schemas.business_redemptions import ConfirmRedemptionRequest, RedemptionResponse
from app.services.redemption import (
    confirm_redemption as confirm_redemption_lifecycle,
)
from app.services.redemption import (
    reject_redemption as reject_redemption_lifecycle,
)
from app.ws.manager import publish
from ws_contracts.events import RedemptionConfirmed

router = APIRouter()


def _redemption_response(db: Session, redemption: Redemption) -> RedemptionResponse:
    drop_title = db.scalar(select(Drop.title).where(Drop.id == redemption.drop_id))
    xp_reward_base = db.scalar(select(Drop.xp_reward_base).where(Drop.id == redemption.drop_id))
    member_count = db.scalar(
        select(func.count())
        .select_from(GroupMember)
        .where(
            GroupMember.group_id == redemption.group_id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    )
    return RedemptionResponse(
        id=str(redemption.id),
        drop_id=str(redemption.drop_id),
        drop_title=drop_title or "",
        group_id=str(redemption.group_id),
        status=redemption.status,
        checked_in_at=redemption.checked_in_at,
        confirmed_at=redemption.confirmed_at,
        participant_count=redemption.participant_count,
        member_count=member_count or 0,
        xp_reward_base=xp_reward_base or 0,
    )


@router.get("", response_model=list[RedemptionResponse])
def list_redemptions(
    redemption_status: RedemptionStatus = RedemptionStatus.checked_in,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    """Defaults to the live queue (checked_in, awaiting confirmation) — pass
    ?redemption_status=confirmed for history."""
    redemptions = db.scalars(
        select(Redemption)
        .where(Redemption.business_id == business.id, Redemption.status == redemption_status)
        .order_by(Redemption.checked_in_at)
    ).all()
    return [_redemption_response(db, redemption) for redemption in redemptions]


@router.post("/{redemption_id}/confirm", response_model=RedemptionResponse)
async def confirm_redemption(
    redemption_id: UUID,
    body: ConfirmRedemptionRequest,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    try:
        redemption, xp_awarded = confirm_redemption_lifecycle(
            db, redemption_id, business.id, business.id, body.participant_count
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    event = RedemptionConfirmed(
        group_id=str(redemption.group_id),
        redemption_id=str(redemption.id),
        xp_awarded=xp_awarded,
    ).model_dump(mode="json")
    for topic in {
        f"ws:group:{redemption.group_id}",
        *(f"ws:user:{user_id}" for user_id in xp_awarded),
    }:
        await publish(topic, event)
    return _redemption_response(db, redemption)


@router.post("/{redemption_id}/reject", response_model=RedemptionResponse)
def reject_redemption(
    redemption_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    try:
        redemption = reject_redemption_lifecycle(db, redemption_id, business.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _redemption_response(db, redemption)
