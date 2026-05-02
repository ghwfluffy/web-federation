# Central Auth Site Phased Implementation

## Phase 0: Architecture And Scaffold

Goal: create the project skeleton and lock the core identity decisions before data is persistent.

Tasks:

- Create the standards-based repo layout: `api/`, `web/`, `nginx/`, `db/`, `scripts/`, `docs/architecture/`, `docs/development.md`.
- Configure Docker Compose for `db`, `api`, `web`, `nginx`, and `db-backup`.
- Set default base path values to `/auth`, while allowing deployment overrides:
  - `APP_BASE_PATH=/auth`
  - `VITE_APP_BASE_PATH=/auth`
  - `VITE_API_BASE_URL=${APP_BASE_PATH}/api/v1`
  - `SESSION_COOKIE_NAME=auth_session`
- Ensure no route, redirect URI, OAuth issuer, avatar URL, cookie path, or frontend link hard-codes `/auth`; all must derive from backend settings or frontend runtime/build config.
- Add `PUBLIC_URL`, explicit CORS origin config, and trusted proxy behavior.
- Add status endpoints and validation scripts.
- Document architecture decisions in `docs/architecture/`.

Exit criteria:

- `docker compose up` starts the empty app.
- the configured base path serves the frontend; with defaults, `/auth` works.
- the configured API base reports app/database status; with defaults, `/auth/api/v1/status` works.
- Validation script runs backend lint/tests and frontend typecheck/tests.

## Phase 1: Core Data Model

Goal: persist central users, sessions, registration codes, OAuth clients, tokens, avatars, and directory entries.

Tables:

- `users`
  - `id`, `username`, `password_hash`, `display_name`, `timezone`, `is_admin`, `is_disabled`, `created_at`, `updated_at`, `password_changed_at`
- `user_profile_images`
  - `id`, `user_id`, `png_bytes`, `sha256`, `width`, `height`, `created_at`
- `auth_sessions`
  - random token hash, user reference, created/last-seen/expires/revoked metadata, user-agent, IP summary
- `registration_codes`
  - secure code hash or code, expiration, revocation, creator, created-user traceability
- `oauth_clients`
  - client id, optional secret hash for confidential clients, display name, redirect URIs, allowed origins, enabled flag
- `oauth_authorization_codes`
  - one-time code hash, user, client, redirect URI, PKCE challenge, scope, expiration, consumed timestamp
- `oauth_refresh_tokens`
  - token hash, user, client, scope, created/expires/revoked/replaced metadata
- `site_directory_entries`
  - site metadata and optional OAuth client link
- `audit_events`
  - auth flows, admin writes, privileged reads where useful

Implementation notes:

- Use UUID-style string primary keys unless there is a concrete reason not to.
- Store timestamps as timezone-aware UTC datetimes.
- Use bcrypt for password hashes.
- Store avatar bytes only after safe PNG re-rendering.
- Hash bearer-like tokens in the database; never store raw session, auth-code, or refresh-token values.
- Add Alembic migration coverage from the start.

Exit criteria:

- Alembic creates all core tables.
- Unit tests cover constraints, uniqueness, token hashing, and migration head.

## Phase 2: First-Party Auth

Goal: implement login, registration, bootstrap, profile, and admin account management under the configured auth base path. Default/example: `/auth`.

Backend API:

- `GET /api/v1/auth/bootstrap-status`
- `POST /api/v1/auth/bootstrap`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `PATCH /api/v1/users/me`
- `POST /api/v1/users/me/avatar`
- `GET /api/v1/users/{user_id}/avatar`
- `POST /api/v1/users/me/change-password`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{user_id}`
- `POST /api/v1/admin/users/{user_id}/reset-password`
- `POST /api/v1/admin/users/{user_id}/disable`
- `POST /api/v1/admin/users/{user_id}/enable`
- `DELETE /api/v1/admin/users/{user_id}`
- `GET /api/v1/admin/registration-codes`
- `POST /api/v1/admin/registration-codes`
- `PATCH /api/v1/admin/registration-codes/{code_id}`
- `POST /api/v1/admin/registration-codes/{code_id}/revoke`
- `DELETE /api/v1/admin/registration-codes/{code_id}` if hard delete is intentionally allowed

Rules:

- The first account can bootstrap without a registration code and becomes admin.
- Later registration requires an active registration code.
- Password change revokes existing sessions and refresh tokens except the current session unless explicitly configured otherwise.
- Admin user deletion must protect the last admin.
- Registration-code revocation is preferred over hard delete for auditability.
- Login and registration are rate-limited in Nginx and guarded in app logic.

Frontend:

- Public route: login/registration/bootstrap page.
- Authenticated shell with four tabs:
  - `Directory`
  - `Users`
  - `Registration Codes`
  - `My Profile`
- Admin-only visibility for `Users` and `Registration Codes`.
- Profile tab owns display name, timezone, password change, avatar upload, and avatar preview.
- Shared API client parses errors and displays user-visible toasts.

Exit criteria:

- Bootstrap, login, logout, registration, profile update, avatar upload, password change, admin user CRUD, and registration-code CRUD work on desktop and mobile.
- Backend tests cover auth/session behavior, admin enforcement, registration-code expiration/revocation, last-admin protections, and avatar safety.
- Frontend tests cover auth-aware navigation and the four-tab shell.

## Phase 3: OAuth/OIDC Provider

Goal: let consumer apps use the configured auth base URL as their identity provider. Default/example: `/auth`.

Backend:

- Add OIDC discovery and JWKS endpoints.
- Add OAuth client administration or seeded client registration.
- Implement Authorization Code with PKCE:
  - validate `client_id`, redirect URI, scope, response type, state, and code challenge
  - require signed-in user or redirect to login
  - issue one-time authorization code
  - exchange code for access token and refresh token
  - revoke refresh tokens
- Add `userinfo` endpoint returning stable central identity claims.
- Add token rotation for refresh tokens.
- Add per-client redirect URI and origin allow-lists.

Claims:

- `sub`: central user UUID
- `preferred_username`
- `name`
- `picture`: absolute avatar URL under the configured auth base path
- `updated_at`
- optional `is_admin`
- optional `roles` or per-client role claim after role model exists

Security:

- Authorization codes expire quickly and are single-use.
- PKCE is required for public browser clients.
- Confidential clients must authenticate at token exchange if client secrets are configured.
- Redirect URIs must match stored values exactly.
- Access tokens are short-lived.
- Refresh tokens are stored as hashes and rotate on use.

Exit criteria:

- A local OAuth client can complete login with PKCE.
- Invalid redirect URI, missing PKCE, reused auth code, expired auth code, revoked refresh token, and disabled user cases are tested.
- Discovery and JWKS endpoints are documented.

## Phase 4: Directory

Goal: make the configured auth base path the signed-in launchpad for related sites. Default/example: `/auth`.

Backend:

- `GET /api/v1/directory/sites`
- Optional admin endpoints for directory CRUD:
  - `GET /api/v1/admin/directory/sites`
  - `POST /api/v1/admin/directory/sites`
  - `PATCH /api/v1/admin/directory/sites/{site_id}`
  - `DELETE /api/v1/admin/directory/sites/{site_id}`

Initial entries:

- Goal Tracker: path/config from `other-sites/goals`
- Fluffynomics: path/config from `other-sites/money-planner`

Frontend:

- Directory tab displays enabled sites with clear names, icons, descriptions, and launch buttons.
- Launch URLs should be generated from configured base URLs, not hard-coded in components.
- If a site has an OAuth client, include an optional "manage access" affordance later, but do not block the first directory release on consent UI unless scopes become user-grantable.

Exit criteria:

- Signed-in users land on the Directory tab.
- Directory links work with configured deployment paths.
- Disabled entries do not appear to normal users.

## Phase 5: Operations And Hardening

Goal: prepare the central auth app to be the identity dependency for all sites.

Tasks:

- Add backup scripts and `db-backup` service.
- Add admin backup list/on-demand backup endpoints.
- Add controlled restore only if needed for this app's operational scope.
- Add audit events for login, logout, registration, password change, avatar change, admin user writes, registration-code writes, OAuth grants, refresh-token use, and token revocation.
- Add Nginx rate limits:
  - strict for bootstrap/login/register/OAuth token exchange
  - general for `/api/`
  - no accidental throttling of avatar image fan-out
- Add production secret validation.
- Add security headers in Nginx.
- Add docs for local development, deployment, backup, restore, and OAuth client configuration.

Exit criteria:

- A fresh environment can be bootstrapped from docs.
- Backups are produced and visible to admins.
- Smoke tests cover login, profile, directory, user admin, registration codes, and OAuth login.
