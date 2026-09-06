"""Add connections (friend requests) and messages (chat) tables.

Revision ID: 0012_connections_and_messages
Revises: 0011_business_venue_capacity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_connections_and_messages"
down_revision = "0011_business_venue_capacity"
branch_labels = None
depends_on = None

connection_status = sa.Enum("pending", "accepted", "declined", "blocked", name="connectionstatus")


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("addressee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", connection_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("requester_id != addressee_id", name="ck_connection_not_self"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_connection_pair"),
    )
    op.create_index("ix_connections_addressee", "connections", ["addressee_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connections.id"), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_connection_created", "messages", ["connection_id", "created_at"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("connections")
    connection_status.drop(op.get_bind())
