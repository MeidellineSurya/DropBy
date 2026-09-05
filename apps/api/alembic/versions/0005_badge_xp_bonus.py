"""Add per-badge passive XP bonus fields.

Revision ID: 0005_badge_xp_bonus
Revises: 0004_powerups
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_badge_xp_bonus"
down_revision = "0004_powerups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "badges",
        sa.Column("xp_bonus_pct", sa.Float(), nullable=False, server_default="0"),
    )
    op.alter_column("badges", "xp_bonus_pct", server_default=None)
    op.add_column("badges", sa.Column("xp_bonus_category", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("badges", "xp_bonus_category")
    op.drop_column("badges", "xp_bonus_pct")
