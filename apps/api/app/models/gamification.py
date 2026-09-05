import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class XpReason(str, enum.Enum):
    drop_completed = "drop_completed"
    badge_unlocked = "badge_unlocked"
    bonus = "bonus"


class BadgeCriteriaType(str, enum.Enum):
    drop_count = "drop_count"
    rarity_collected = "rarity_collected"
    category_explored = "category_explored"
    city_progress = "city_progress"
    squad_leader_count = "squad_leader_count"


class UserXpTransaction(Base):
    __tablename__ = "user_xp_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[XpReason] = mapped_column(Enum(XpReason))
    related_redemption_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String, nullable=True)
    criteria_type: Mapped[BadgeCriteriaType] = mapped_column(Enum(BadgeCriteriaType))
    criteria_config: Mapped[dict] = mapped_column(JSONB, default=dict)


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    badge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("badges.id"), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserStats(Base):
    """Denormalized rollup, owned by app/services/gamification.py."""

    __tablename__ = "user_stats"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    total_drops_completed: Mapped[int] = mapped_column(Integer, default=0)
    cities_explored: Mapped[dict] = mapped_column(JSONB, default=dict)
    rarity_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
