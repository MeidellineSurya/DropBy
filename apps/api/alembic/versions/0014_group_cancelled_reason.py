"""Persist Group.cancelled_reason — previously only ever returned
transiently in the one response that caused the cancellation, never stored,
so any later read (a WS-triggered refresh, a poll) always saw None.

Revision ID: 0014_group_cancelled_reason
Revises: 0013_redemption_disputed
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_group_cancelled_reason"
down_revision = "0013_redemption_disputed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("cancelled_reason", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("groups", "cancelled_reason")
