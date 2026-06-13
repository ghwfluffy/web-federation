# Auth And OAuth

The auth site owns first-party login, registration, password changes, profile metadata, avatars, admin user management, registration codes, and OAuth/OIDC identity for consumer sites.

The default public base path is `/auth`, but callers must use the configured `PUBLIC_URL` plus `APP_BASE_PATH`. OAuth discovery is served from `${AUTH_BASE_URL}/.well-known/openid-configuration`.

## OAuth Flow

- Consumer apps use Authorization Code with PKCE.
- `/oauth/authorize` requires an existing central auth session and issues a short-lived code.
- `/oauth/token` exchanges a valid code and PKCE verifier for an access token and refresh token.
- `/oauth/userinfo` returns the stable central subject, username, display name, avatar URL, updated timestamp, and admin flag.
- `/oauth/revoke` revokes refresh tokens.

Consumer apps should keep their own app-scoped cookies after callback. They must not reuse or depend on the central auth session cookie.

## Required Client Data

Each OAuth client needs a unique client id, display name, enabled flag, and exact redirect URI allow-list. Browser clients are public clients and must use PKCE S256.

The auth API lazily creates the default first-party clients when OAuth authorization
or default directory seeding runs and the client rows do not already exist:

- `goals`, redirecting to `${PUBLIC_URL}${GOALS_BASE_URL}/api/v1/auth/oauth/callback`
- `money-planner`, redirecting to `${PUBLIC_URL}${MONEY_PLANNER_BASE_URL}/api/auth/oauth/callback`
- `agent`, redirecting to `${PUBLIC_URL}${AGENT_BASE_URL}/api/v1/auth/oauth/callback`
- `apartment-gate`, redirecting to `${PUBLIC_URL}${APARTMENT_GATE_BASE_URL}/auth/oauth/callback`

Existing client rows are not overwritten by the defaults. This lets operators
customize or disable clients intentionally while still making fresh databases
usable from configuration alone.
