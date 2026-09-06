import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RedemptionStatus(str, enum.Enum):
    pending = "pending"
    checked_in = "checked_in"
    confirmed = "confirmed"
    rejected = "rejected"
    expired = "expired"


class Redemption(Base):
    """Owned by the redemption/gamification module.

    One Redemption per Group: it is created and auto-confirmed in the same
    step the moment a member claims check-in (see services/redemption.py) —
    there is no business approval gate. A business can instead dispute a
    confirmed redemption within DISPUTE_WINDOW as a fraud/mistake flag;
    disputing does NOT claw back XP already awarded (that would also need to
    unwind badges/streaks/stats derived from it, which isn't built — see
    STATUS.md). `checked_in`/`rejected` are legacy values from the old
    QR-scan-then-business-confirms flow, unused by new redemptions.
    """

    __tablename__ = "redemptions"
    __table_args__ = (UniqueConstraint("group_id", name="uq_redemption_group"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drops.id"))
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"))
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))

    status: Mapped[RedemptionStatus] = mapped_column(Enum(RedemptionStatus), default=RedemptionStatus.pending)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    participant_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
