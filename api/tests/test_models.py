from __future__ import annotations

from app.db.models import (
    AuthSession,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthRefreshToken,
    RegistrationCode,
    SiteDirectoryEntry,
    User,
)


def unique_constraint_names(model: type[object]) -> set[str]:
    return {constraint.name or "" for constraint in model.__table__.constraints}


def test_core_tables_have_expected_uniqueness_constraints() -> None:
    assert "uq_users_username" in unique_constraint_names(User)
    assert "uq_registration_codes_code_hash" in unique_constraint_names(RegistrationCode)
    assert "uq_auth_sessions_token_hash" in unique_constraint_names(AuthSession)
    assert "uq_oauth_clients_client_id" in unique_constraint_names(OAuthClient)
    assert "uq_oauth_authorization_codes_code_hash" in unique_constraint_names(OAuthAuthorizationCode)
    assert "uq_oauth_refresh_tokens_token_hash" in unique_constraint_names(OAuthRefreshToken)
    assert "uq_site_directory_entries_slug" in unique_constraint_names(SiteDirectoryEntry)


def test_user_defaults_are_standalone_safe() -> None:
    user = User(username="admin", password_hash="hash")

    assert user.is_admin is None
    assert user.is_disabled is None
    assert user.timezone is None
    assert User.timezone.default is not None
    assert User.timezone.default.arg == "America/Chicago"
