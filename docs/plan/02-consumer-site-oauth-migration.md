# Consumer Site OAuth Migration Plan

## Goal

Update `other-sites/goals` and `other-sites/money-planner` so they can optionally use the configured central auth base URL as the OAuth/OIDC identity provider. The default mode for both consumer apps must remain standalone local authentication so they can be developed, tested, and deployed independently. The default/example central auth base path is `/auth`, but consumer apps must only depend on `AUTH_BASE_URL`, not a hard-coded path.

Each consumer app should:

- Continue to use built-in users, registration, password, and profile flows when central IAM is disabled.
- Redirect login, registration, user management, password changes, and profile icon management to the configured auth base URL only when central IAM is enabled.
- Keep app-domain authorization and user-owned data boundaries.
- Maintain an app-scoped session cookie with a unique name and path.
- Resolve the signed-in user's profile icon from the configured auth base URL only in central IAM mode.
- Stop collecting passwords or registration codes locally only in central IAM mode.

## Auth Mode Requirement

Both consumer apps need an explicit authentication mode setting.

Recommended setting:

- `AUTH_MODE=local`: default; use the app's built-in user, registration, password, profile, and session flows.
- `AUTH_MODE=oauth`: use the central auth app for login, registration, user management, password changes, and human profile icons.

Rules:

- Missing or invalid config must fail closed to `local` in development/test and log a warning in production.
- OAuth configuration is required only when `AUTH_MODE=oauth`.
- Existing local auth endpoints and UI remain available in `local` mode.
- OAuth redirects and central profile/user-management links are active only in `oauth` mode.
- App-domain settings remain local in both modes.
- Tests must cover both modes.

## Shared Consumer Configuration

Add equivalent settings to both apps:

- `AUTH_MODE=local`
- `AUTH_BASE_URL`: external base URL for the identity app, including the configured base path. Default/example: `/auth`.
- `OAUTH_ISSUER`: normally same as `AUTH_BASE_URL`.
- `OAUTH_CLIENT_ID`
- `OAUTH_CLIENT_SECRET` if using confidential server-side exchange.
- `OAUTH_REDIRECT_URI`
- `OAUTH_SCOPES=openid profile`
- `USER_MANAGEMENT_URL=${AUTH_BASE_URL}/users` or the final configured route.
- `PROFILE_URL=${AUTH_BASE_URL}/profile` or the final configured route.
- `DIRECTORY_URL=${AUTH_BASE_URL}` or the final configured route.
- `SESSION_COOKIE_NAME`: app-specific.
- `SESSION_COOKIE_PATH`: app base path, not `/`.

Cookie requirements:

- `goals`: keep or rename `goal_tracker_session`, but set cookie path to the goals app base path.
- `money-planner`: keep `mp_session`, continue path scoping with `APP_BASE_PATH`.
- `auth-site`: use `auth_session`, path from configured auth `APP_BASE_PATH`; default/example path is `/auth`.
- All cookies must be HTTP-only, `SameSite=Lax`, secure outside development/test, and not shared across apps.

## Shared Migration Pattern

1. Add `AUTH_MODE` configuration with `local` as the default.
2. Add OAuth client configuration and discovery loading, but initialize it only when `AUTH_MODE=oauth`.
3. Add a local OAuth login route that redirects to `${AUTH_BASE_URL}/oauth/authorize` only in OAuth mode.
4. Add an OAuth callback route that exchanges the authorization code only in OAuth mode.
5. Validate token signature, issuer, audience, expiration, nonce/state, and PKCE.
6. Upsert or link a local app user record using central `sub`.
7. Create an app-local session cookie scoped to the app path.
8. Update `/auth/me` or the equivalent current-user endpoint to return local app user plus central profile summary in OAuth mode, and the current local profile shape in local mode.
9. Update logout to clear only the app cookie and optionally offer central logout link in OAuth mode.
10. Keep local login/register/password/profile management forms in local mode.
11. Hide or redirect native user-management/profile routes to configured `AUTH_BASE_URL` targets only in OAuth mode.

Local user records should keep app-specific data ownership. Add a central identity key:

- `identity_provider`
- `external_subject`
- unique constraint on `(identity_provider, external_subject)`
- optional `username_snapshot`
- optional `display_name_snapshot`
- optional `avatar_url_snapshot`
- `last_identity_sync_at`

Do not use mutable username as the primary cross-app identifier.

## `goals` Migration

### Backend

Current local auth surfaces:

- `/api/v1/auth/bootstrap-status`
- `/api/v1/auth/bootstrap`
- `/api/v1/auth/login`
- `/api/v1/auth/register`
- `/api/v1/auth/me`
- `/api/v1/auth/logout`
- `/api/v1/users/me`
- `/api/v1/users/me/avatar`
- `/api/v1/users/me/change-password`
- `/api/v1/invitation-codes`

Phased backend changes:

1. Add settings:
   - `auth_mode`, default `local`
   - `auth_base_url`
   - `oauth_issuer`
   - `oauth_client_id`
   - `oauth_client_secret`
   - `oauth_redirect_uri`
   - `oauth_scopes`
   - `session_cookie_path`
2. Change session cookie path handling in `api/app/api/routes/auth.py` from `/` to the configured app base path.
3. Add migration to `users`:
   - `identity_provider`
   - `external_subject`
   - uniqueness for linked central identities.
4. Add OAuth callback service and route, enabled only when `auth_mode=oauth`.
5. Adjust local `get_current_user` to keep using the app session after OAuth login.
6. Keep domain ownership checks unchanged; they should continue to rely on the local `users.id`.
7. Keep local bootstrap/register/login endpoints active in `local` mode.
8. In `oauth` mode, redirect or return explicit disabled responses for local bootstrap/register/login endpoints.
9. Replace `/api/v1/users/me/avatar` reads with central avatar URL in auth payload only in `oauth` mode; keep the local endpoint active in `local` mode.
10. Keep `/api/v1/invitation-codes` active in `local` mode; in `oauth` mode, redirect or return explicit disabled responses after the central auth app owns registration codes.

### Frontend

Current local UI surfaces:

- Guest login/register/bootstrap in `GuestHomePanel.vue`.
- Profile/password/avatar/invitation-code modals in `HomeProfileDialogs.vue`.
- Header avatar URL points to `/api/v1/users/me/avatar`.

Phased frontend changes:

1. Add `VITE_AUTH_MODE=local` and `VITE_AUTH_BASE_URL`.
2. Keep the current unauthenticated login/register/bootstrap UI in local mode.
3. In OAuth mode, change unauthenticated state to show a sign-in button linking to the local OAuth login route.
4. In OAuth mode, change registration links to `${AUTH_BASE_URL}` registration route.
5. In OAuth mode, change profile edit/password/avatar menu items to configured `PROFILE_URL` or `AUTH_BASE_URL` targets.
6. In OAuth mode, change invitation-code menu item to configured registration-code management URL for admins.
7. In OAuth mode, change avatar rendering to use the `picture` or `avatar_url` returned by `/api/v1/auth/me`.
8. Keep local profile and invitation-code dialogs in local mode.
9. Keep share-link and backup dialogs local because they are app-domain features, not identity features.

### Data Migration

Options:

- Automatic link by exact username if the central user already exists.
- Admin-assisted link screen listing unlinked local users.
- First OAuth login creates a new local user if no exact link exists.

Recommended first pass:

- Add admin-only linking command/script before disabling local login.
- Link existing local users to central `sub`.
- Keep local user IDs unchanged so goal/dashboard/share data does not move.

## `money-planner` Migration

### Backend

Current local auth surfaces:

- `/auth/register`
- `/auth/login`
- `/auth/logout`
- `/auth/me`
- `/auth/profile`
- `/auth/widget-url/regenerate`
- `/auth/delete-account`
- `/admin/users`
- `/admin/registration-codes`

Phased backend changes:

1. Add settings:
   - `AUTH_MODE`, default `local`
   - `AUTH_BASE_URL`
   - `OAUTH_ISSUER`
   - `OAUTH_CLIENT_ID`
   - `OAUTH_CLIENT_SECRET`
   - `OAUTH_REDIRECT_URI`
   - `OAUTH_SCOPES`
2. Replace Fernet stateless sessions with server-side app sessions if feasible. If not done in the same phase, keep the existing cookie temporarily but issue it only after OAuth callback.
3. Keep `mp_session` scoped to `APP_BASE_PATH`.
4. Add migration to `users`:
   - `identity_provider`
   - `external_subject`
   - unique constraint.
5. Add OAuth callback route under `/auth/callback`, enabled only when `AUTH_MODE=oauth`.
6. Update `get_current_user` to load the local user from the app session created after OAuth callback in OAuth mode while preserving existing local-session behavior in local mode.
7. Keep returning `session_token` JSON for local login in local mode.
8. Redirect or retire local register/login/password/profile avatar behavior only in OAuth mode.
9. Keep wallet-account profile fields local if they are app-domain preferences.
10. Move admin user CRUD and registration-code CRUD out of `money-planner` navigation and into configured auth management URLs only in OAuth mode.

### Frontend

Current local UI surfaces:

- `web/vue/src/auth/LandingPage.vue` login/register form.
- `web/vue/src/AppShell.vue` profile modal, admin user modal, registration code CRUD.
- `web/vue/src/lib/auth.ts` local auth client.

Phased frontend changes:

1. Add `VITE_AUTH_MODE=local` and `VITE_AUTH_BASE_URL`.
2. Keep the current landing login/register actions in local mode.
3. Convert landing login/register actions to OAuth redirects only in OAuth mode.
4. Change Manage Users menu item to `${AUTH_BASE_URL}` user management only in OAuth mode.
5. Change registration-code UI to `${AUTH_BASE_URL}` registration-code tab only in OAuth mode.
6. Split profile modal in OAuth mode:
   - central identity profile/password/avatar opens configured `PROFILE_URL` or `AUTH_BASE_URL`
   - app-domain preferences such as PayPal/Google Pay account mapping remain local.
7. Render profile image from central `picture` claim or central avatar URL only in OAuth mode.
8. Keep widget URL regeneration local because it controls the money-planner public widget.
9. Keep local password fields in local mode; hide them in OAuth mode.

### Data Migration

Recommended first pass:

- Link existing local users to central `sub` by admin script or exact username match.
- Preserve local `users.id` because accounts, contracts, expenses, investments, logs, backups, and widgets are user-scoped.
- Keep `is_admin` local until a central role policy is explicitly chosen.
- After validation, disable local registration and password login.

## User Management Redirect Behavior

Each consumer app should treat identity management as external only when central IAM is enabled:

- In OAuth mode, native `/users`, `/admin/users`, `/registration-codes`, `/profile/password`, and `/profile/avatar` routes should redirect to configured `AUTH_BASE_URL`.
- In local mode, native user-management, registration-code, password, and profile-avatar flows should continue to work locally.
- Redirect targets should preserve a `return_to` query parameter back to the calling app where practical.
- If the consumer app uses modal-only user management today, menu actions should navigate directly to configured auth management URLs.

Suggested central routes, assuming the default `/auth` base path:

- `/auth`: directory
- `/auth/profile`: my profile
- `/auth/users`: admin users
- `/auth/registration-codes`: admin registration codes

## Profile Icon Contract

Central identity owns human profile icons.

Recommended API contract:

- `/api/v1/users/{user_id}/avatar` serves the latest PNG for central users.
- `/api/v1/auth/me` and `/oauth/userinfo` include `picture`.
- `picture` is an absolute URL and includes a version query parameter when possible.
- Consumer apps cache normally but refresh when `updated_at` or `avatar_version` changes.

Consumer apps should not proxy central avatars unless an app-specific privacy or CORS issue appears.

## Logout Contract

Default behavior:

- Consumer app logout clears only that app's session cookie.
- Provide an optional "Sign out everywhere" link/action that sends the user to the configured central logout URL or calls a future central logout endpoint.

Do not clear other apps' cookies from a consumer app.

## Compatibility Window

During rollout:

- Keep local auth tables in place.
- Keep local user IDs stable.
- Add central subject linkage columns.
- Allow local admin scripts to repair links.
- Disable local browser login only after OAuth login works for existing users.
- Remove local password hashes only after a backup and a successful production-like validation pass.
