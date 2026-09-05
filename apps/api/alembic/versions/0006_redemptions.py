"""Create the redemptions table — the business check-in/confirm flow.

Revision ID: 0006_redemptions
Revises: 0005_business_venue_capacity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_redemptions"
down_revision = "0005_business_venue_capacity"
branch_labels = None
depends_on = None

redemption_status = sa.Enum(
    "pending", "checked_in", "confirmed", "rejected", "expired", name="redemptionstatus"
)


def upgrade() -> None:
    op.create_table(
        "redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "drop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drops.id"), nullable=False
        ),
        sa.Column(
            "group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False
        ),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id"),
            nullable=False,
        ),
        sa.Column("status", redemption_status, nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("group_id", name="uq_redemption_group"),
    )
    op.create_index(
        "ix_redemptions_business_status", "redemptions", ["business_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_redemptions_business_status", table_name="redemptions")
    op.drop_table("redemptions")
    redemption_status.drop(op.get_bind())
