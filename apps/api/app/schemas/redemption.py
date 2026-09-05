from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.redemption import RedemptionStatus


class CheckInRequest(BaseModel):
    qr_token: str


class ConfirmRequest(BaseModel):
    # Business can correct the headcount actually present; omit to accept
    # the squad's current joined member count as-is.
    participant_count: int | None = None


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drop_id: UUID
    group_id: UUID
    business_id: UUID
    status: RedemptionStatus
    checked_in_at: datetime | None
    confirmed_at: datetime | None
    participant_count: int | None


class VenueQrResponse(BaseModel):
    qr_token: str
