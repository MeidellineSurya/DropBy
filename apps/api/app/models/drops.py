import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base


class DropCategory(str, enum.Enum):
    food_dining = "food_dining"
    activity_entertainment = "activity_entertainment"
    nightlife = "nightlife"
    wellness_beauty = "wellness_beauty"
    retail = "retail"
    other = "other"


class DropRarity(str, enum.Enum):
    common = "common"
    uncommon = "uncommon"
    rare = "rare"
    epic = "epic"
    legendary = "legendary"


class DropType(str, enum.Enum):
    solo = "solo"
    squad = "squad"
    raid = "raid"


class DropStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    active = "active"
    paused = "paused"
    capacity_reached = "capacity_reached"
    expired = "expired"
    completed = "completed"
    cancelled = "cancelled"


class Drop(Base):
    """Config fields are written by the business module; status/reserved_count are
    written only by app/services/drop_lifecycle.py."""

    __tablename__ = "drops"
    __table_args__ = (
        CheckConstraint(
            "discovery_radius_m >= reveal_radius_m", name="ck_drop_detect_reveal_radius"
        ),
        CheckConstraint(
            "reveal_radius_m >= discover_radius_m",
            name="ck_drop_reveal_discover_radius",
        ),
        CheckConstraint("min_group_size > 0", name="ck_drop_min_group_positive"),
        CheckConstraint("max_group_size >= min_group_size", name="ck_drop_group_range"),
        CheckConstraint(
            "reserved_count <= max_capacity_participants", name="ck_drop_capacity"
        ),
        CheckConstraint("reserved_count >= 0", name="ck_drop_reserved_nonnegative"),
        Index("ix_drops_status_time", "status", "starts_at", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id")
    )

    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[DropCategory] = mapped_column(Enum(DropCategory))
    rarity: Mapped[DropRarity] = mapped_column(
        Enum(DropRarity), default=DropRarity.common
    )
    drop_type: Mapped[DropType] = mapped_column(Enum(DropType))

    min_group_size: Mapped[int] = mapped_column(Integer, default=1)
    max_group_size: Mapped[int] = mapped_column(Integer, default=1)

    location: Mapped[str] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    discovery_radius_m: Mapped[int] = mapped_column(
        Integer, default=settings.default_detect_radius_m
    )
    reveal_radius_m: Mapped[int] = mapped_column(
        Integer, default=settings.default_reveal_radius_m
    )
    discover_radius_m: Mapped[int] = mapped_column(
        Integer, default=settings.default_discover_radius_m
    )

    max_capacity_participants: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    xp_reward_base: Mapped[int] = mapped_column(Integer, default=10)

    status: Mapped[DropStatus] = mapped_column(
        Enum(DropStatus), default=DropStatus.draft
    )
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DropViewStage(str, enum.Enum):
    detect = "detect"
    reveal = "reveal"
    discover = "discover"


class DropViewEvent(Base):
    """Cross-cutting: written by the discovery module, read by business analytics
    and gamification exploration achievements."""

    __tablename__ = "drop_view_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "drop_id", "stage", name="uq_drop_view_user_drop_stage"
        ),
        Index("ix_drop_view_user_drop", "user_id", "drop_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    drop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drops.id")
    )
    stage: Mapped[DropViewStage] = mapped_column(Enum(DropViewStage))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
