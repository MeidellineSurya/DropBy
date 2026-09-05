from datetime import datetime

from pydantic import BaseModel, Field

from app.models.drops import DropCategory, DropRarity, DropType, DropViewStage


class LocationPingRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DropSnapshot(BaseModel):
    id: str
    stage: DropViewStage
    distance_m: int
    rarity: DropRarity | None = None
    category: DropCategory | None = None
    title: str | None = None
    description: str | None = None
    business_name: str | None = None
    address: str | None = None
    drop_type: DropType | None = None
    min_group_size: int | None = None
    max_group_size: int | None = None
    ends_at: datetime | None = None
    can_assemble: bool | None = None


class LocationPingResponse(BaseModel):
    drops: list[DropSnapshot]
