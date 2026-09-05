from datetime import datetime

from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.drops import DropCategory, DropRarity, DropStatus, DropType


class BusinessDropCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    category: DropCategory
    drop_type: DropType
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    max_capacity_participants: int = Field(gt=0)
    starts_at: datetime
    ends_at: datetime
    description: str | None = Field(default=None, max_length=2000)
    # Shown even at Detect (see services/proximity.py); falls back to the
    # category label if omitted.
    interest_tag: str | None = Field(default=None, max_length=60)
    rarity: DropRarity = DropRarity.common
    min_group_size: int = Field(default=1, gt=0)
    max_group_size: int = Field(default=1, gt=0)
    discovery_radius_m: int = Field(default=settings.default_detect_radius_m, gt=0)
    discover_radius_m: int = Field(default=settings.default_discover_radius_m, gt=0)
    # Vestigial middle radius from the retired three-stage model — the DB still
    # enforces discovery_radius_m >= reveal_radius_m >= discover_radius_m, but
    # the two-stage engine never reads it. Left optional so callers don't need
    # to know it exists; the route derives a valid midpoint when omitted.
    reveal_radius_m: int | None = Field(default=None, gt=0)
    xp_reward_base: int = Field(default=10, ge=0)
    publish: bool = False


class BusinessDropResponse(BaseModel):
    id: str
    title: str
    description: str | None
    category: DropCategory
    interest_tag: str
    rarity: DropRarity
    drop_type: DropType
    min_group_size: int
    max_group_size: int
    discovery_radius_m: int
    discover_radius_m: int
    max_capacity_participants: int
    reserved_count: int
    starts_at: datetime
    ends_at: datetime
    status: DropStatus
    xp_reward_base: int
