import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RedemptionStatus(str, enum.Enum):
    # Reserved for a future eager-create-at-"ready" flow; nothing creates a
    # Redemption in this status today — see services/redemption.check_in_group.
    pending = "pending"
    checked_in = "checked_in"
    confirmed = "confirmed"
    rejected = "rejected"
    # Reserved for a future expiry sweep (mirroring drop_lifecycle.expire_due);
    # nothing transitions a Redemption into this status today.
    expired = "expired"


class Redemption(Base):
    """Owned by the redemption/gamification module."""

    __tablename__ = "redemptions"
    __table_args__ = (
        UniqueConstraint("group_id", name="uq_redemption_group"),
        Index("ix_redemptions_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drops.id"))
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"))
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))

    status: Mapped[RedemptionStatus] = mapped_column(Enum(RedemptionStatus), default=RedemptionStatus.pending)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    participant_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
