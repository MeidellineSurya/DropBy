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
    rarity: DropRarity = DropRarity.common
    min_group_size: int = Field(default=1, gt=0)
    max_group_size: int = Field(default=1, gt=0)
    discovery_radius_m: int = Field(default=settings.default_detect_radius_m, gt=0)
    reveal_radius_m: int = Field(default=settings.default_reveal_radius_m, gt=0)
    discover_radius_m: int = Field(default=settings.default_discover_radius_m, gt=0)
    xp_reward_base: int = Field(default=10, ge=0)
    publish: bool = False


class BusinessDropResponse(BaseModel):
    id: str
    title: str
    description: str | None
    category: DropCategory
    rarity: DropRarity
    drop_type: DropType
    min_group_size: int
    max_group_size: int
    discovery_radius_m: int
    reveal_radius_m: int
    discover_radius_m: int
    max_capacity_participants: int
    reserved_count: int
    starts_at: datetime
    ends_at: datetime
    status: DropStatus
    xp_reward_base: int
