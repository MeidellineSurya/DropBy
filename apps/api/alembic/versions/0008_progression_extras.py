"""Add time-of-day perks, rarity-set badges, territory exploration, and
weekly challenges.

Revision ID: 0008_progression_extras
Revises: 0007_streak_shield
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_progression_extras"
down_revision = "0007_streak_shield"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE perktype ADD VALUE IF NOT EXISTS 'time_specialization'")
    op.execute("ALTER TYPE badgecriteriatype ADD VALUE IF NOT EXISTS 'rarity_set_per_category'")

    op.add_column(
        "user_stats",
        sa.Column("category_rarity_sets", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.alter_column("user_stats", "category_rarity_sets", server_default=None)

    op.create_table(
        "user_explored_cells",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("cell", sa.String(), primary_key=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "weekly_challenge_claims",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("week_key", sa.String(), primary_key=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("xp_awarded", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("weekly_challenge_claims")
    op.drop_table("user_explored_cells")
    op.drop_column("user_stats", "category_rarity_sets")
    # Postgres cannot drop a single enum value without rebuilding the type;
    # the two new enum values are left in place on downgrade.
