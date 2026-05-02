# Rollout And Validation Checklist

## Phase Order

1. Build the central auth foundation and first-party auth using `/auth` as the default base path.
2. Add central profile, avatar, admin users, and registration-code management.
3. Add OAuth/OIDC provider endpoints and seeded clients for `goals` and `money-planner`.
4. Add directory entries and launch links.
5. Migrate `goals` to OAuth.
6. Migrate `money-planner` to OAuth.
7. Disable native auth/user-management flows in consumer apps.
8. Remove old password/register/profile code after backups and validation.

## Environment Matrix

Validate these deployment shapes:

- Local dev without outer proxy.
- Local production-style Nginx with the configured auth base path; default/example `/auth`.
- Same host with all three apps mounted under distinct paths.
- HTTPS behind an outer proxy.

Minimum expected paths:

- `${AUTH_BASE_URL}`
- `${AUTH_BASE_URL}/api/v1/status`
- goals app base path
- money-planner app base path

## Cookie Validation

Verify in browser devtools and automated smoke tests:

- `auth_session` path matches configured auth `APP_BASE_PATH`; default/example `/auth`.
- `goal_tracker_session` path is the goals app base path.
- `mp_session` path is the money-planner app base path.
- No app sets a generic same-name cookie at `/`.
- All production cookies are secure and HTTP-only.
- Logout from one app does not delete unrelated app cookies.

## Backend Tests

`auth-site`:

- bootstrap first admin
- reject second bootstrap
- login/logout/session expiration/session revocation
- password change invalidates sessions and refresh tokens
- registration code create/update/revoke/expire
- registration code traceability to created users
- admin user CRUD and last-admin protection
- avatar upload validates size/type and re-renders PNG
- OAuth authorize/token/userinfo happy path
- OAuth invalid redirect URI
- OAuth missing/invalid PKCE
- OAuth reused/expired auth code
- OAuth revoked refresh token
- disabled user cannot authenticate or refresh
- directory filtering

`goals`:

- OAuth callback creates app session.
- Central `sub` links to local user.
- Domain ownership checks still reject cross-user access.
- Local login/register/profile/password/avatar routes redirect or are disabled as planned.
- Cookie path is app-scoped.
- Auth payload includes central avatar URL.

`money-planner`:

- OAuth callback creates app session.
- Central `sub` links to local user.
- Domain ownership checks still reject cross-user access.
- Local login/register/password/avatar routes redirect or are disabled as planned.
- Existing widget-token behavior remains local.
- Cookie path remains app-scoped.

## Frontend Tests

`auth-site`:

- unauthenticated user sees login/register/bootstrap surface
- authenticated user lands on Directory tab
- non-admin cannot see or access Users and Registration Codes tabs
- admin can create/update/disable users
- admin can create/update/revoke registration codes
- profile can update display name/timezone/password/avatar
- mobile layout keeps tabs/forms usable

Consumer apps:

- unauthenticated user gets OAuth login redirect
- OAuth callback returns to app shell
- header/profile image uses central avatar URL
- user-management menu opens configured auth user-management URL
- registration-code management opens configured auth registration-code URL
- app-domain profile preferences remain available only where still local

## End-To-End Smoke

Run a full three-app smoke:

1. Start `auth-site`, `goals`, and `money-planner` on the same host with distinct base paths.
2. Bootstrap the first central admin.
3. Create registration code.
4. Register a non-admin user through `${AUTH_BASE_URL}`.
5. Log in to `${AUTH_BASE_URL}`.
6. Confirm the directory shows both consumer sites.
7. Launch Goal Tracker from the directory and complete OAuth login.
8. Create or view a goal as the linked user.
9. Launch Fluffynomics from the directory and complete OAuth login.
10. View accounts/dashboard as the linked user.
11. Change avatar in `${AUTH_BASE_URL}`.
12. Confirm both consumer app headers show the updated avatar URL.
13. Open user management from each consumer app and confirm it redirects to the configured auth user-management URL.
14. Log out of one consumer app and confirm the other app and central auth app behave according to the logout contract.

## Data Migration Checklist

Before migration:

- Create backups for `goals`, `money-planner`, and `auth-site`.
- Export existing local users from both consumer apps.
- Decide exact username auto-link policy.
- Create central users or invite users.
- Record central `sub` for each migrated account.

During migration:

- Add identity-link columns.
- Backfill `identity_provider=<configured issuer key>` and `external_subject`.
- Preserve local `users.id`.
- Keep local admin flags unless central role mapping is explicitly implemented.
- Disable local browser registration first, then local browser password login.

After migration:

- Verify every user-owned domain record still resolves to the intended local user.
- Verify admin-only screens remain protected.
- Verify backups still work.
- Verify no consumer app can create a new local password account from the browser.
- Schedule deletion or archival of obsolete local password hashes.

## Rollback Plan

Rollback should be possible until local auth is removed.

Steps:

- Re-enable consumer local login feature flag.
- Keep identity-link columns; they are additive.
- Restore previous frontend login/profile menu if needed.
- Do not delete local password hashes until the OAuth rollout has survived a production-like validation period.

If the configured central auth app is unavailable after cutover:

- Existing consumer app sessions may continue until they expire.
- New logins will fail.
- User management, password changes, registration, and avatar changes are unavailable until central auth is restored.
- Operational priority is restoring the central auth database and API before changing consumer apps.

## Documentation Updates

Add or update:

- `auth-site/docs/architecture/auth-oauth.md`
- `auth-site/docs/architecture/data-model.md`
- `auth-site/docs/architecture/site-directory.md`
- `auth-site/docs/development.md`
- `goals/docs/architecture/auth-migration-auth.md`
- `money-planner/docs/architecture/auth-migration-auth.md`
- `.env.example` in all three repos
- deployment notes for same-host cookie path behavior

## Definition Of Done

The migration is complete when:

- the central auth app owns login, registration, profile image, password change, users, and registration codes.
- Both consumer apps use OAuth for new sessions.
- Both consumer apps redirect identity management to configured auth management URLs.
- Consumer cookies are app-scoped and do not collide.
- Existing user-owned data remains attached to the correct local users.
- Directory launch links work for both apps.
- Backend, frontend, and end-to-end smoke tests pass.
