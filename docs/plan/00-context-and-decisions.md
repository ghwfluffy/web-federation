# Central Auth Context And Decisions

## Purpose

Build `auth-site` as the central identity, profile, registration, user-management, and site-directory application for the local site family.

The default externally mounted base path is `/auth`, but it must be deploy-time configurable everywhere. The app is intentionally more than a login screen: after sign-in it becomes the directory landing page for other sites and the single place to manage users, registration codes, password changes, and profile icons.

## Inputs Read

- `docs/project-standards/README.md`
- `docs/project-standards/default-stack.md`
- `docs/project-standards/repository-layout.md`
- `docs/project-standards/backend-standards.md`
- `docs/project-standards/frontend-standards.md`
- `docs/project-standards/api-standards.md`
- `docs/project-standards/auth-and-authorization.md`
- `docs/project-standards/security-standards.md`
- `docs/project-standards/data-modeling-and-migrations.md`
- `docs/project-standards/testing-and-quality.md`
- `docs/project-standards/operations-backup-restore.md`
- `docs/project-standards/delivery-checklist.md`
- `other-sites/goals`
- `other-sites/money-planner`

## Standards To Follow

- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, bcrypt, `cryptography`, pytest, httpx.
- Frontend: Vue 3, Vite, TypeScript, Pinia, Vue Router, PrimeVue, PrimeIcons.
- Sessions: server-side records in PostgreSQL with opaque signed HTTP-only cookies.
- Registration: first account bootstraps as admin; later registration requires admin-managed registration codes.
- Uploads: profile images must be validated, resized, and re-rendered to a safe PNG before serving.
- APIs: versioned under `/api/v1`, with explicit schemas and stable error messages.
- Operations: Docker Compose with `db`, `api`, `web`, `nginx`, and `db-backup`.
- Base path: frontend routes, generated URLs, cookies, OAuth issuer metadata, redirect URLs, avatar URLs, and proxy config must derive from configuration. Use `/auth` as the default/example value only.

## Current Consumer Site Inventory

### `other-sites/goals`

- Stack matches the newer standards: FastAPI, Alembic, PostgreSQL, Vue 3, Vite, Pinia, PrimeVue.
- Auth is local and DB-backed with `auth_sessions`.
- Cookie name is `goal_tracker_session`.
- Cookie path is currently `/`, so it needs explicit path/base-path scoping before multiple same-host apps share an origin.
- Auth routes live under `/api/v1/auth`.
- Profile routes live under `/api/v1/users/me`, including avatar upload and password change.
- Registration-code routes live under `/api/v1/invitation-codes`.
- Profile, backup, share-link, and invitation-code UI currently lives in `HomeProfileDialogs.vue`.

### `other-sites/money-planner`

- Stack is FastAPI/PostgreSQL/Vue/Vite, but frontend uses Carbon/Vuetify-era local patterns instead of PrimeVue.
- Auth is local and stateless: encrypted/signed Fernet session token containing `user_id` and `expires_at`.
- Cookie name is `mp_session`.
- Cookie path is already scoped through `APP_BASE_PATH`.
- Auth routes live under `/auth`.
- Admin user CRUD and registration-code CRUD live under `/admin`.
- Profile/password/avatar wallet preferences live under `/auth/profile`.
- Public image/icon endpoints are app-domain icons, not central identity avatars.

## Naming Decisions

- Product/repo role: central identity and site directory.
- Runtime base path default: `/auth`.
- Required configuration key: `APP_BASE_PATH` on the auth app, mirrored into frontend build/runtime config as `VITE_APP_BASE_PATH`.
- Suggested cookie name for this app: `auth_session`.
- Suggested OAuth issuer: `${PUBLIC_URL}${APP_BASE_PATH}`; with defaults, `${PUBLIC_URL}/auth`.
- Suggested API base: `${APP_BASE_PATH}/api/v1`; with defaults, `/auth/api/v1`.
- Suggested frontend app base: `${APP_BASE_PATH}`; with defaults, `/auth`.

## OAuth/OIDC Direction

Use OAuth 2.0 Authorization Code with PKCE and OIDC-style identity endpoints. This is the cleanest migration path for browser apps and server-side APIs without sharing raw passwords or central cookies with consumer apps.

Minimum provider surface:

- `GET /.well-known/openid-configuration`
- `GET /oauth/authorize`
- `POST /oauth/token`
- `POST /oauth/revoke`
- `GET /oauth/userinfo`
- `GET /oauth/jwks.json`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

Recommended token shape:

- Short-lived signed access token.
- Optional refresh token stored server-side as a hash.
- Stable `sub` claim equal to the central user UUID.
- Claims: `preferred_username`, `name`, `picture`, `updated_at`, `is_admin`, and app-specific role claims only when granted.

Consumer apps should keep their own app-scoped session cookies after OAuth callback. They should not read or set the central auth session cookie, whose path must come from configured `APP_BASE_PATH`.

## Site Directory Direction

Store known sites in the identity app, not hard-coded only in the frontend.

Site fields:

- `id`
- `slug`
- `name`
- `description`
- `base_url`
- `icon_url` or PrimeIcon key
- `is_enabled`
- `display_order`
- optional `oauth_client_id`
- optional `required_role`
- timestamps

Authenticated users see enabled directory entries they are allowed to access. Admins can later manage site metadata if needed, but the first implementation can seed the two known sites from configuration or migration data.

## High-Risk Areas

- Account identity migration from local `users.id` to central `sub`.
- User-owned data preservation while removing native registration/login.
- Cookie collisions on same-host deployments.
- Password-change invalidation across central sessions, refresh tokens, and consumer sessions.
- Avatar URL access rules and cache invalidation.
- Admin permissions after centralization, especially last-admin safeguards.
- Redirect URL validation for OAuth clients.
- Cross-site logout expectations.

## Open Decisions Before Implementation

- Whether existing local usernames are authoritative for account linking, or whether each user must manually link once.
- Whether central admins are automatically admins in every consumer app, or whether per-site roles are separate.
- Whether consumer apps keep local user rows as app profiles keyed by central `sub`, or replace local users entirely.
- Whether registration codes are global only, or can be scoped to specific allowed sites.
- Whether directory entries are config-seeded, admin-editable, or both.
- Whether old local password hashes should be deleted immediately after migration or retained briefly behind a disabled fallback.
