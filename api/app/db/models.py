from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="America/Chicago")
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registration_code_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("registration_codes.id", name="fk_users_registration_code_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile_images: Mapped[list[UserProfileImage]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    used_registration_code: Mapped[RegistrationCode | None] = relationship(
        back_populates="created_users",
        foreign_keys=[registration_code_id],
    )
    created_registration_codes: Mapped[list[RegistrationCode]] = relationship(
        back_populates="created_by_user",
        foreign_keys="RegistrationCode.created_by_user_id",
    )


class UserProfileImage(Base):
    __tablename__ = "user_profile_images"
    __table_args__ = (UniqueConstraint("sha256", name="uq_user_profile_images_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_user_profile_images_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    png_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped[User] = relationship(back_populates="profile_images")


class RegistrationCode(Base):
    __tablename__ = "registration_codes"
    __table_args__ = (UniqueConstraint("code_hash", name="uq_registration_codes_code_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_registration_codes_created_by_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    created_by_user: Mapped[User | None] = relationship(
        back_populates="created_registration_codes",
        foreign_keys=[created_by_user_id],
    )
    created_users: Mapped[list[User]] = relationship(
        back_populates="used_registration_code",
        foreign_keys="User.registration_code_id",
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_auth_sessions_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    __table_args__ = (UniqueConstraint("client_id", name="uq_oauth_clients_client_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    client_secret_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    redirect_uris: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_origins: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    authorization_codes: Mapped[list[OAuthAuthorizationCode]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list[OAuthRefreshToken]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )
    directory_entries: Mapped[list[SiteDirectoryEntry]] = relationship(back_populates="oauth_client")


class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"
    __table_args__ = (UniqueConstraint("code_hash", name="uq_oauth_authorization_codes_code_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_oauth_authorization_codes_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("oauth_clients.id", name="fk_oauth_authorization_codes_client_id", ondelete="CASCADE"),
        nullable=False,
    )
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(String(500), nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(200), nullable=False)
    code_challenge_method: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[OAuthClient] = relationship(back_populates="authorization_codes")


class OAuthRefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_oauth_refresh_tokens_token_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_oauth_refresh_tokens_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("oauth_clients.id", name="fk_oauth_refresh_tokens_client_id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "oauth_refresh_tokens.id",
            name="fk_oauth_refresh_tokens_replaced_by_token_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    client: Mapped[OAuthClient] = relationship(back_populates="refresh_tokens", foreign_keys=[client_id])


class SiteDirectoryEntry(Base):
    __tablename__ = "site_directory_entries"
    __table_args__ = (UniqueConstraint("slug", name="uq_site_directory_entries_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    oauth_client_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("oauth_clients.id", name="fk_site_directory_entries_oauth_client_id", ondelete="SET NULL"),
        nullable=True,
    )
    required_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    oauth_client: Mapped[OAuthClient | None] = relationship(back_populates="directory_entries")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_audit_events_actor_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
