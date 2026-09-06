"""Add Redemption.disputed_at for the business-side dispute window.

Revision ID: 0013_redemption_disputed
Revises: 0012_connections_and_messages
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_redemption_disputed"
down_revision = "0012_connections_and_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "redemptions",
        sa.Column("disputed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("redemptions", "disputed_at")
