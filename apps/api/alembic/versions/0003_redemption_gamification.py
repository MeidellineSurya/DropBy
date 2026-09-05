"""Create the redemption, gamification, and notification tables.

Revision ID: 0003_redemption_gamification
Revises: 0002_detect_interest_tag
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_redemption_gamification"
down_revision = "0002_detect_interest_tag"
branch_labels = None
depends_on = None

redemption_status = sa.Enum(
    "pending", "checked_in", "confirmed", "rejected", "expired", name="redemptionstatus"
)
xp_reason = sa.Enum("drop_completed", "badge_unlocked", "bonus", name="xpreason")
badge_criteria_type = sa.Enum(
    "drop_count",
    "rarity_collected",
    "category_explored",
    "city_progress",
    "squad_leader_count",
    name="badgecriteriatype",
)
notification_type = sa.Enum(
    "drop_nearby",
    "squad_invite",
    "squad_ready",
    "countdown_warning",
    "drop_expiring",
    "redemption_confirmed",
    "badge_unlocked",
    name="notificationtype",
)
push_status = sa.Enum("sent", "failed", "skipped", name="pushstatus")


def upgrade() -> None:
    op.create_table(
        "user_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("fcm_token", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_devices_user", "user_devices", ["user_id"])

    op.create_table(
        "redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("drop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drops.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("status", redemption_status, nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("group_id", name="uq_redemption_group"),
    )
    op.create_index("ix_redemptions_business_status", "redemptions", ["business_id", "status"])

    op.create_table(
        "user_xp_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", xp_reason, nullable=False),
        sa.Column("related_redemption_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_xp_transactions_user", "user_xp_transactions", ["user_id"])
    op.create_index(
        "ix_user_xp_transactions_redemption", "user_xp_transactions", ["related_redemption_id"]
    )

    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("icon_url", sa.String(), nullable=True),
        sa.Column("criteria_type", badge_criteria_type, nullable=False),
        sa.Column("criteria_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_badges_code", "badges", ["code"], unique=True)

    op.create_table(
        "user_badges",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("badges.id"), primary_key=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("total_drops_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cities_explored", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rarity_counts", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("category_counts", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_redemption_date", sa.Date(), nullable=True),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("push_status", push_status, nullable=False),
    )
    op.create_index("ix_notification_log_user", "notification_log", ["user_id"])


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("user_stats")
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("user_xp_transactions")
    op.drop_table("redemptions")
    op.drop_table("user_devices")
    push_status.drop(op.get_bind())
    notification_type.drop(op.get_bind())
    badge_criteria_type.drop(op.get_bind())
    xp_reason.drop(op.get_bind())
    redemption_status.drop(op.get_bind())
