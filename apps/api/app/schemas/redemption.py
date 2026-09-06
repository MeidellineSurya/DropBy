from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.redemption import RedemptionStatus


class ConfirmRequest(BaseModel):
    # Business can correct the headcount actually present; omit to accept
    # the squad's current joined member count as-is.
    participant_count: int | None = None


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
    # Dashboard display fields, not columns on Redemption itself — populated
    # by the route from the Drop and the Group's current joined members.
    member_count: int
    xp_reward_base: int
