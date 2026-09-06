from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.redemption import RedemptionStatus


class SquadQrResponse(BaseModel):
    qr_token: str


class ScanRequest(BaseModel):
    qr_token: str


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drop_id: UUID
    drop_title: str
    group_id: UUID
    business_id: UUID
    status: RedemptionStatus
    checked_in_at: datetime | None
    confirmed_at: datetime | None
    participant_count: int | None
    disputed_at: datetime | None
    # Dashboard display fields, not columns on Redemption itself — populated
    # by the route from the Drop and the Group's current joined members.
    member_count: int
    xp_reward_base: int
