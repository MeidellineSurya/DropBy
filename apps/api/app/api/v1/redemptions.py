from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business
from app.models.groups import Group
from app.schemas.redemption import RedemptionResponse, ScanRequest
from app.services.redemption import build_response, dispute_redemption, list_recent_redemptions, scan_squad_qr
from app.services.squad_state import group_snapshot
from app.workers.tasks.gamification import award_xp_for_redemption_task
from app.ws.manager import publish
from ws_contracts.events import RedemptionCheckedIn

router = APIRouter()


@router.get("/queue", response_model=list[RedemptionResponse])
def recent_redemptions(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[RedemptionResponse]:
    """Confirmed redemptions still inside the dispute window."""
    return [build_response(db, redemption) for redemption in list_recent_redemptions(db, business)]


@router.post("/scan", response_model=RedemptionResponse)
async def scan(
    body: ScanRequest,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    """Staff scan a squad's check-in code. This is the actual verification +
    confirmation step — see services/redemption.py's module docstring for
    why the business, not the squad's own location, is the trust anchor."""
    redemption = scan_squad_qr(db, body.qr_token, business)
    group = db.get(Group, redemption.group_id)
    if group is not None:
        snapshot = group_snapshot(db, group)
        event = RedemptionCheckedIn(
            group_id=snapshot.id,
            redemption_id=str(redemption.id),
            checked_in_at=redemption.checked_in_at,
        ).model_dump(mode="json")
        for topic in {
            f"ws:group:{snapshot.id}",
            *(f"ws:user:{member.user_id}" for member in snapshot.members),
        }:
            await publish(topic, event)
    award_xp_for_redemption_task.delay(str(redemption.id))
    return build_response(db, redemption)


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
