from pydantic import BaseModel

from app.models.drops import DropStatus


class DropFunnelResponse(BaseModel):
    drop_id: str
    status: DropStatus
    # Two-stage discovery model (see services/proximity.py): "detect_count" is
    # everyone who ever saw the mystery pin; "revealed_count" is everyone who
    # got close enough to unlock the full offer (stored internally as the
    # legacy "discover" DropViewStage value — there is no longer a distinct
    # persisted middle stage).
    detect_count: int
    revealed_count: int
    reserved_count: int
    max_capacity_participants: int
    squads_forming: int
    squads_ready: int
    squads_completed: int


class BusinessOverviewResponse(BaseModel):
    active_drops: int
    draft_drops: int
    scheduled_drops: int
    total_reserved_participants: int
    total_capacity_participants: int
    distinct_viewers_last_7_days: int
