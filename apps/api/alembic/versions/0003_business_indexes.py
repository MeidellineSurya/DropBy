"""Add spatial and lookup indexes for business-side proximity/listing queries.

Revision ID: 0003_business_indexes
Revises: 0002_detect_interest_tag
"""

from alembic import op

revision = "0003_business_indexes"
down_revision = "0002_detect_interest_tag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_drops_location_gist",
        "drops",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_businesses_location_gist",
        "businesses",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index("ix_drops_business_id", "drops", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_drops_business_id", table_name="drops")
    op.drop_index("ix_businesses_location_gist", table_name="businesses")
    op.drop_index("ix_drops_location_gist", table_name="drops")
