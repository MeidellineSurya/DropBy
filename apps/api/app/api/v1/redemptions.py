from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business
from app.schemas.redemption import RedemptionResponse
from app.services.redemption import build_response, dispute_redemption, list_recent_redemptions

router = APIRouter()


@router.get("/queue", response_model=list[RedemptionResponse])
def recent_redemptions(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    """Confirmed redemptions still inside the dispute window."""
    return [build_response(db, redemption) for redemption in list_recent_redemptions(db, business)]


@router.post("/{redemption_id}/dispute", response_model=RedemptionResponse)
def dispute(
    redemption_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Business flags a confirmed redemption as fraudulent or mistaken,
    releasing its reserved capacity back to the Drop. Does not claw back XP
    already awarded — see services/redemption.py."""
    redemption = dispute_redemption(db, redemption_id, business)
    return build_response(db, redemption)
