from pydantic import BaseModel

from app.models.drops import DropStatus


class DropFunnelResponse(BaseModel):
    drop_id: str
    status: DropStatus
    detect_count: int
    reveal_count: int
    discover_count: int
    reserved_count: int
    max_capacity_participants: int
    squads_forming: int
    squads_ready: int
    squads_checked_in: int
    squads_completed: int


class BusinessOverviewResponse(BaseModel):
    active_drops: int
    draft_drops: int
    scheduled_drops: int
    total_reserved_participants: int
    total_capacity_participants: int
    distinct_viewers_last_7_days: int
