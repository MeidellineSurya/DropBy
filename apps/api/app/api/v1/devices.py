from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.users import User
from app.schemas.notifications import DeviceResponse, RegisterDeviceRequest
from app.services.notifications import register_device

router = APIRouter()


@router.post("", response_model=DeviceResponse, status_code=201)
def register(
    body: RegisterDeviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceResponse:
    """The mobile app calls this once it has an FCM token, so push
    notifications (squad ready, redemption confirmed, badge unlocked, nearby
    Rare+ Drops, countdown warnings) can actually reach the phone."""
    device = register_device(db, user.id, body.fcm_token, body.platform)
    return DeviceResponse(id=str(device.id), platform=device.platform, active=device.active)
