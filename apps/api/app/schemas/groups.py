from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.groups import GroupMemberRole, GroupMemberStatus, GroupStatus


class GroupCreateRequest(BaseModel):
    drop_id: UUID
    open_to_nearby: bool = True


class GroupMemberResponse(BaseModel):
    user_id: str
    display_name: str
    role: GroupMemberRole
    status: GroupMemberStatus


class GroupResponse(BaseModel):
    id: str
    drop_id: str
    created_by_user_id: str
    status: GroupStatus
    current_count: int
    min_required: int
    max_allowed: int
    open_to_nearby: bool
    expires_at: datetime | None
    members: list[GroupMemberResponse]
    # Set by services/squad_state.py when a reserve_capacity() race cancels
    # this squad, so members see the real reason instead of an unexplained
    # cancellation (see services/drop_lifecycle.describe_capacity_failure).
    cancelled_reason: str | None = None
