import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(str, enum.Enum):
    drop_nearby = "drop_nearby"
    squad_invite = "squad_invite"
    squad_ready = "squad_ready"
    countdown_warning = "countdown_warning"
    drop_expiring = "drop_expiring"
    redemption_confirmed = "redemption_confirmed"
    badge_unlocked = "badge_unlocked"


class PushStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    push_status: Mapped[PushStatus] = mapped_column(Enum(PushStatus), default=PushStatus.sent)
