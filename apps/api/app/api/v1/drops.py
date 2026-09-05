from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.users import User
from app.schemas.drops import DropSnapshot, LocationPingRequest, LocationPingResponse
from app.services.proximity import compute_stage_for_ping, get_discovered_drop

router = APIRouter()


@router.post(
    "/location/ping",
    response_model=LocationPingResponse,
    response_model_exclude_none=True,
)
async def location_ping(
    body: LocationPingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationPingResponse:
    drops = await compute_stage_for_ping(db, user, body.latitude, body.longitude)
    return LocationPingResponse(drops=drops)


@router.get("/{drop_id}", response_model=DropSnapshot, response_model_exclude_none=True)
def get_drop(
    drop_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DropSnapshot:
    drop = get_discovered_drop(db, user.id, drop_id)
    if drop is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Move close enough to Discover this Drop first"
        )
    return drop
