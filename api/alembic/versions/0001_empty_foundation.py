"""create core identity tables

Revision ID: 0001_empty_foundation
Revises:
Create Date: 2026-05-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_empty_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registration_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code_hash", name="uq_registration_codes_code_hash"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("registration_code_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["registration_code_id"],
            ["registration_codes.id"],
            name="fk_users_registration_code_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_foreign_key(
        "fk_registration_codes_created_by_user_id",
        "registration_codes",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "user_profile_images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("png_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profile_images_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("sha256", name="uq_user_profile_images_sha256"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_sessions_user_id", ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )

    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("client_id", sa.String(length=100), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("allowed_origins", sa.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", name="uq_oauth_clients_client_id"),
    )

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("redirect_uri", sa.String(length=500), nullable=False),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("code_challenge", sa.String(length=200), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["oauth_clients.id"],
            name="fk_oauth_authorization_codes_client_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_oauth_authorization_codes_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("code_hash", name="uq_oauth_authorization_codes_code_hash"),
    )

    op.create_table(
        "oauth_refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["oauth_clients.id"],
            name="fk_oauth_refresh_tokens_client_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            ["oauth_refresh_tokens.id"],
            name="fk_oauth_refresh_tokens_replaced_by_token_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_oauth_refresh_tokens_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_oauth_refresh_tokens_token_hash"),
    )

    op.create_table(
        "site_directory_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("oauth_client_id", sa.String(length=36), nullable=True),
        sa.Column("required_role", sa.String(length=100), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["oauth_client_id"],
            ["oauth_clients.id"],
            name="fk_site_directory_entries_oauth_client_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("slug", name="uq_site_directory_entries_slug"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_events_actor_user_id",
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("site_directory_entries")
    op.drop_table("oauth_refresh_tokens")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")
    op.drop_table("auth_sessions")
    op.drop_table("user_profile_images")
    op.drop_constraint("fk_registration_codes_created_by_user_id", "registration_codes", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("registration_codes")
