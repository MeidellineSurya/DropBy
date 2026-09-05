from datetime import datetime

from pydantic import BaseModel

from app.models.redemption import RedemptionStatus


class RedemptionResponse(BaseModel):
    id: str
    drop_id: str
    drop_title: str
    group_id: str
    status: RedemptionStatus
    checked_in_at: datetime | None
    confirmed_at: datetime | None
    # Record-keeping only — see services/redemption.py's module docstring for
    # why this never adjusts Drop.reserved_count.
    participant_count: int | None
    member_count: int
    xp_reward_base: int


class ConfirmRedemptionRequest(BaseModel):
    # Optional headcount correction; defaults to the squad's joined-member
    # count when omitted.
    participant_count: int | None = None
