"""Add the discount_percent value signal rarity is computed from.

Revision ID: 0010_drop_discount_percent
Revises: 0009_business_indexes
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_drop_discount_percent"
down_revision = "0009_business_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "drops",
        sa.Column(
            "discount_percent",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
    )
    op.alter_column("drops", "discount_percent", server_default=None)
    op.create_check_constraint(
        "ck_drop_discount_percent_range",
        "drops",
        "discount_percent >= 1 AND discount_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_drop_discount_percent_range", "drops", type_="check")
    op.drop_column("drops", "discount_percent")
