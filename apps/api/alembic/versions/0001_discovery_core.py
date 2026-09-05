"""Create the shared prerequisites and discovery-engine tables.

Revision ID: 0001_discovery_core
Revises:
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision = "0001_discovery_core"
down_revision = None
branch_labels = None
depends_on = None

business_status = sa.Enum("pending", "active", "suspended", name="businessstatus")
drop_category = sa.Enum(
    "food_dining",
    "activity_entertainment",
    "nightlife",
    "wellness_beauty",
    "retail",
    "other",
    name="dropcategory",
)
drop_rarity = sa.Enum("common", "uncommon", "rare", "epic", "legendary", name="droprarity")
drop_type = sa.Enum("solo", "squad", "raid", name="droptype")
drop_status = sa.Enum(
    "draft",
    "scheduled",
    "active",
    "paused",
    "capacity_reached",
    "expired",
    "completed",
    "cancelled",
    name="dropstatus",
)
drop_view_stage = sa.Enum("detect", "reveal", "discover", name="dropviewstage")
group_status = sa.Enum(
    "forming", "ready", "checked_in", "completed", "expired", "cancelled", name="groupstatus"
)
member_role = sa.Enum("leader", "member", name="groupmemberrole")
member_status = sa.Enum("invited", "joined", "left", name="groupmemberstatus")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("preferences", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("location_permission", sa.String(), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_location", Geography(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("last_location_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xp_total", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("owner_email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("status", business_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owner_email"),
    )
    op.create_index("ix_businesses_owner_email", "businesses", ["owner_email"], unique=True)

    op.create_table(
        "drops",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", drop_category, nullable=False),
        sa.Column("rarity", drop_rarity, nullable=False),
        sa.Column("drop_type", drop_type, nullable=False),
        sa.Column("min_group_size", sa.Integer(), nullable=False),
        sa.Column("max_group_size", sa.Integer(), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("discovery_radius_m", sa.Integer(), nullable=False),
        sa.Column("reveal_radius_m", sa.Integer(), nullable=False),
        sa.Column("discover_radius_m", sa.Integer(), nullable=False),
        sa.Column("max_capacity_participants", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("xp_reward_base", sa.Integer(), nullable=False),
        sa.Column("status", drop_status, nullable=False),
        sa.Column("reserved_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("discovery_radius_m >= reveal_radius_m", name="ck_drop_detect_reveal_radius"),
        sa.CheckConstraint("reveal_radius_m >= discover_radius_m", name="ck_drop_reveal_discover_radius"),
        sa.CheckConstraint("min_group_size > 0", name="ck_drop_min_group_positive"),
        sa.CheckConstraint("max_group_size >= min_group_size", name="ck_drop_group_range"),
        sa.CheckConstraint("reserved_count <= max_capacity_participants", name="ck_drop_capacity"),
        sa.CheckConstraint("reserved_count >= 0", name="ck_drop_reserved_nonnegative"),
    )
    op.create_index("ix_drops_status_time", "drops", ["status", "starts_at", "ends_at"])

    op.create_table(
        "drop_view_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("drop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drops.id"), nullable=False),
        sa.Column("stage", drop_view_stage, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "drop_id", "stage", name="uq_drop_view_user_drop_stage"),
    )
    op.create_index("ix_drop_view_user_drop", "drop_view_events", ["user_id", "drop_id"])

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("drop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drops.id"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", group_status, nullable=False),
        sa.Column("min_required", sa.Integer(), nullable=False),
        sa.Column("max_allowed", sa.Integer(), nullable=False),
        sa.Column("open_to_nearby", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("min_required > 0", name="ck_group_min_positive"),
        sa.CheckConstraint("max_allowed >= min_required", name="ck_group_size_range"),
    )
    op.create_index("ix_groups_drop_status", "groups", ["drop_id", "status"])

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", member_role, nullable=False),
        sa.Column("status", member_status, nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )
    op.create_index("ix_group_members_user", "group_members", ["user_id"])

    op.create_table(
        "group_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("invite_code", sa.String(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uses_remaining", sa.Integer(), nullable=False),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_index("ix_group_invites_invite_code", "group_invites", ["invite_code"], unique=True)


def downgrade() -> None:
    op.drop_table("group_invites")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("drop_view_events")
    op.drop_table("drops")
    op.drop_table("businesses")
    op.drop_table("users")
    member_status.drop(op.get_bind())
    member_role.drop(op.get_bind())
    group_status.drop(op.get_bind())
    drop_view_stage.drop(op.get_bind())
    drop_status.drop(op.get_bind())
    drop_type.drop(op.get_bind())
    drop_rarity.drop(op.get_bind())
    drop_category.drop(op.get_bind())
    business_status.drop(op.get_bind())
