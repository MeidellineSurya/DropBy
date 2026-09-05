"""Frozen WebSocket event contract.

Every event published over the `ws:*` Redis topics (and delivered to
mobile/dashboard clients via app/ws/manager.py) must be defined here first.
Do not redefine payload shapes elsewhere — both frontends generate their TS
types from this module (see packages/shared-types).
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class Envelope(BaseModel):
    type: str
    payload: dict
    ts: datetime


class Stage(str, Enum):
    detect = "detect"
    reveal = "reveal"


class DropStageUpdate(BaseModel):
    type: Literal["drop.stage_update"] = "drop.stage_update"
    drop_id: str
    stage: Stage
    distance_m: int
    data: dict


class DropCapacityReached(BaseModel):
    type: Literal["drop.capacity_reached"] = "drop.capacity_reached"
    drop_id: str


class DropExpired(BaseModel):
    type: Literal["drop.expired"] = "drop.expired"
    drop_id: str
    reason: Literal["time", "capacity", "cancelled"]


class DropCountdownWarning(BaseModel):
    type: Literal["drop.countdown_warning"] = "drop.countdown_warning"
    drop_id: str
    minutes_remaining: int


class GroupMemberSummary(BaseModel):
    user_id: str
    display_name: str
    role: Literal["leader", "member"]
    status: Literal["invited", "joined", "left"]


class GroupStateUpdate(BaseModel):
    type: Literal["group.state_update"] = "group.state_update"
    group_id: str
    drop_id: str
    status: Literal["forming", "ready", "checked_in", "completed", "expired", "cancelled"]
    current_count: int
    min_required: int
    max_allowed: int
    members: list[GroupMemberSummary]
    expires_at: datetime | None = None
    # Set when status == cancelled/expired so members see *why* — e.g. "This
    # Drop is temporarily paused by the business" vs "reached full capacity"
    # (see services/drop_lifecycle.describe_capacity_failure). None otherwise.
    reason: str | None = None


class GroupMemberJoined(BaseModel):
    type: Literal["group.member_joined"] = "group.member_joined"
    group_id: str
    user_id: str
    display_name: str
    current_count: int


class GroupReady(BaseModel):
    type: Literal["group.ready"] = "group.ready"
    group_id: str
    drop_id: str
    venue_directions_url: str


class RedemptionCheckedIn(BaseModel):
    type: Literal["redemption.checked_in"] = "redemption.checked_in"
    group_id: str
    redemption_id: str
    checked_in_at: datetime


class RedemptionConfirmed(BaseModel):
    type: Literal["redemption.confirmed"] = "redemption.confirmed"
    group_id: str
    redemption_id: str
    xp_awarded: dict[str, int]


class BadgeUnlocked(BaseModel):
    type: Literal["badge.unlocked"] = "badge.unlocked"
    badge_code: str
    name: str
    icon_url: str | None = None


class PowerupGranted(BaseModel):
    type: Literal["powerup.granted"] = "powerup.granted"
    powerup_type: str
    count: int


class TerritoryBonusAwarded(BaseModel):
    type: Literal["territory.bonus_awarded"] = "territory.bonus_awarded"
    cell: str
    xp_awarded: int
