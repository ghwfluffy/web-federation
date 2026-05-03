# Operations And Security Decisions

This file records project-specific decisions and approved deviations from the reusable standards.

## API Error Contract

API errors use one JSON envelope:

```json
{
  "error": {
    "code": "http_401",
    "message": "Not authenticated.",
    "field_errors": [],
    "request_id": "request-id"
  }
}
```

- `code` is stable enough for client branching.
- `message` is safe for user-visible frontend toast text.
- `field_errors` is used for validation details.
- `request_id` is echoed in the `X-Request-ID` response header.

The frontend API client parses this envelope and falls back to generic status text only when the response is malformed.

## Threat Model Checklist

Protected data:

- Password hashes, session tokens, OAuth authorization codes, refresh tokens, registration codes, and profile images.
- User profile metadata and central identity relationships for connected apps.
- Backup artifacts under `./backups`.

Public surfaces:

- Login, registration, bootstrap status, OAuth metadata, OAuth authorization/token/userinfo/revocation, health/status, and avatar URLs.
- Authenticated identity, directory, admin, profile, registration-code, and backup APIs.

Privileged actions:

- Bootstrap, admin user management, registration-code lifecycle, manual backup creation, directory administration, OAuth client configuration, password changes, and avatar uploads.

Current controls:

- Server-side PostgreSQL sessions keyed by hashed random tokens.
- HTTP-only session cookies scoped to the configured base path.
- Secure cookies outside development/test.
- Nginx rate limits for general API traffic and stricter auth endpoints.
- Conservative avatar handling by re-rendering uploaded images to PNG before storage.
- Audit events for auth flows and privileged writes where practical.
- Production startup failure for unsafe default secrets and local public URLs.

Known risks to revisit before broader production exposure:

- Application-level login lockout counters are not persisted yet; ingress rate limiting is the current abuse brake.
- Backup metadata is manifest-file based rather than persisted in normal application tables.
- Controlled in-app restore is intentionally out of scope for now.

## Backup And Restore Scope

Automatic backups are managed by the `central_db_backup` Compose service and write dump files plus JSON manifests under `./backups`.

Admins can list backup manifests and trigger on-demand backups through `/api/v1/admin/backups`. The current implementation treats manifest files as the backup index. This is an approved short-term deviation from the reusable default that recommends a `backup_records` table.

Restore is intentionally an operator-run emergency procedure for this app. There is no browser-triggered restore endpoint or restore operation table until controlled in-app restore becomes an explicit requirement. Emergency restore steps live in `docs/development.md`.
