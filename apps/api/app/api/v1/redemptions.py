from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business
from app.schemas.redemption import ConfirmRequest, RedemptionResponse
from app.services.redemption import (
    build_response,
    confirm_redemption,
    list_redemption_queue,
    reject_redemption,
)
from app.workers.tasks.gamification import award_xp_for_redemption_task

router = APIRouter()


@router.get("/queue", response_model=list[RedemptionResponse])
def redemption_queue(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    """The business dashboard's live redemption queue (checked-in, awaiting confirm)."""
    return [build_response(db, redemption) for redemption in list_redemption_queue(db, business)]


@router.post("/{redemption_id}/confirm", response_model=RedemptionResponse)
def confirm(
    redemption_id: UUID,
    body: ConfirmRequest,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Business confirms headcount, completes the Group, and enqueues XP/badge award."""
    redemption = confirm_redemption(db, redemption_id, business, body.participant_count)
    award_xp_for_redemption_task.delay(str(redemption.id))
    return build_response(db, redemption)


@router.post("/{redemption_id}/reject", response_model=RedemptionResponse)
def reject(
    redemption_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Business rejects a mistaken or fraudulent claim, releasing the squad's
    reserved capacity back to the Drop."""
    redemption = reject_redemption(db, redemption_id, business)
    return build_response(db, redemption)
