import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GroupStatus(str, enum.Enum):
    forming = "forming"
    ready = "ready"
    checked_in = "checked_in"
    completed = "completed"
    expired = "expired"
    cancelled = "cancelled"


class GroupMemberRole(str, enum.Enum):
    leader = "leader"
    member = "member"


class GroupMemberStatus(str, enum.Enum):
    invited = "invited"
    joined = "joined"
    left = "left"


class Group(Base):
    """A 'Squad' — owned by the discovery module (app/services/squad_state.py)."""

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drops.id"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    status: Mapped[GroupStatus] = mapped_column(Enum(GroupStatus), default=GroupStatus.forming)

    # Snapshotted from the Drop at creation time so an in-flight squad's target
    # can't shift if the business edits a draft/paused Drop afterwards.
    min_required: Mapped[int] = mapped_column(Integer)
    max_allowed: Mapped[int] = mapped_column(Integer)

    open_to_nearby: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    role: Mapped[GroupMemberRole] = mapped_column(Enum(GroupMemberRole), default=GroupMemberRole.member)
    status: Mapped[GroupMemberStatus] = mapped_column(Enum(GroupMemberStatus), default=GroupMemberStatus.invited)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GroupInvite(Base):
    __tablename__ = "group_invites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"))
    invite_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uses_remaining: Mapped[int] = mapped_column(Integer, default=1)
