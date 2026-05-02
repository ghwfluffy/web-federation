# Data Model

The core identity schema is owned by Alembic.

- `users`: central account records, admin flags, disabled flags, password metadata, and profile fields.
- `user_profile_images`: safe PNG avatar bytes and metadata.
- `registration_codes`: invite-style registration codes, expiration, revocation, and creator.
- `auth_sessions`: central first-party session records keyed by a hashed random token.
- `oauth_clients`: registered consumer applications and redirect allow-lists.
- `oauth_authorization_codes`: short-lived PKCE authorization codes.
- `oauth_refresh_tokens`: hashed refresh tokens with rotation and revocation metadata.
- `site_directory_entries`: launch links shown in the authenticated directory.
- `audit_events`: durable trace records for identity, admin, OAuth, backup, and directory writes.

Avatars are stored in the database, so normal database backups include profile images.
