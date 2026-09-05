"""Add powerups and the powerup_granted notification type.

Revision ID: 0004_powerups
Revises: 0003_redemption_gamification
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_powerups"
down_revision = "0003_redemption_gamification"
branch_labels = None
depends_on = None

powerup_type = sa.Enum(
    "extra_time",
    "xp_boost",
    "bigger_reveal",
    "double_or_nothing",
    "extra_slot",
    name="poweruptype",
)


def upgrade() -> None:
    op.create_table(
        "user_powerups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", powerup_type, nullable=False),
        sa.Column("granted_from_redemption_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_on_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_powerups_user_unused", "user_powerups", ["user_id", "used_at"])
    # New enum values must be added outside the value's first use; safe here
    # since this migration doesn't reference 'powerup_granted' itself.
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'powerup_granted'")


def downgrade() -> None:
    op.drop_table("user_powerups")
    powerup_type.drop(op.get_bind())
    # Postgres cannot drop a single enum value without rebuilding the type;
    # 'powerup_granted' is left in notificationtype on downgrade.
