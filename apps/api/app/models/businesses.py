import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class Business(Base):
    """Owned by the business/supply module."""

    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint(
            "venue_capacity > 0 AND venue_capacity <= 10000",
            name="ck_business_venue_capacity_range",
        ),
        Index("ix_businesses_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    location: Mapped[str] = mapped_column(Geography(geometry_type="POINT", srid=4326))
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    # Declared once at registration, not re-declarable per Drop — see
    # services/drop_lifecycle.compute_rarity. A per-Drop capacity field costs
    # a business nothing to lowball for a rarity bump; this is a one-time
    # commitment about their actual venue that applies to every Drop they
    # ever create, so lying about it has a real, permanent cost (it caps
    # every future Drop too) instead of a free per-transaction one.
    venue_capacity: Mapped[int] = mapped_column(Integer)

    owner_email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    verified: Mapped[bool] = mapped_column(default=False)
    status: Mapped[BusinessStatus] = mapped_column(Enum(BusinessStatus), default=BusinessStatus.pending)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
