"""Add the level-milestone perk system.

Revision ID: 0006_user_perks
Revises: 0005_badge_xp_bonus
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_user_perks"
down_revision = "0005_badge_xp_bonus"
branch_labels = None
depends_on = None

perk_type = sa.Enum(
    "bigger_radius", "extra_powerup_slot", "category_specialization", name="perktype"
)


def upgrade() -> None:
    op.create_table(
        "user_perks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("milestone_level", sa.Integer(), nullable=False),
        sa.Column("type", perk_type, nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_perks_user", "user_perks", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_perks")
    perk_type.drop(op.get_bind())
