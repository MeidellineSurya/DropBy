"""Add streak_shield powerup and streak_grace perk enum values.

Revision ID: 0007_streak_shield
Revises: 0006_user_perks
"""

from alembic import op

revision = "0007_streak_shield"
down_revision = "0006_user_perks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE poweruptype ADD VALUE IF NOT EXISTS 'streak_shield'")
    op.execute("ALTER TYPE perktype ADD VALUE IF NOT EXISTS 'streak_grace'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value without rebuilding the type;
    # these values are left in place on downgrade.
    pass
