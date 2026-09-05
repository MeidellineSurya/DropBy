"""Add Business.venue_capacity, declared once at registration.

Revision ID: 0011_business_venue_capacity
Revises: 0010_drop_discount_percent
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_business_venue_capacity"
down_revision = "0010_drop_discount_percent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "venue_capacity",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),
    )
    op.alter_column("businesses", "venue_capacity", server_default=None)
    op.create_check_constraint(
        "ck_business_venue_capacity_range",
        "businesses",
        "venue_capacity > 0 AND venue_capacity <= 10000",
    )


def downgrade() -> None:
    op.drop_constraint("ck_business_venue_capacity_range", "businesses", type_="check")
    op.drop_column("businesses", "venue_capacity")
