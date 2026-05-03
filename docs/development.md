# Development

## Local Defaults

Edit `.env` and adjust values as needed. The default external base path is `/auth`.

```sh
docker compose up --build
```

With the defaults:

- Frontend through Nginx: `http://localhost:8190/auth`
- API status through Nginx: `http://localhost:8190/auth/api/v1/status`
- Vite dev server: `http://localhost:8191/auth`

## Validation

```sh
./scripts/validate.sh
```

The validation scripts install or refresh backend and frontend dependencies when needed, then run backend linting, backend tests, frontend tests, and the frontend production build.

## Backups

Automatic backups run through the `central_db_backup` Compose service and write dump files plus JSON manifests under `./backups`.

Admins can list manifests and trigger a manual backup through `/api/v1/admin/backups`. The API container needs `pg_dump`, `BACKUP_DIR`, and `BACKUP_SCRIPT_PATH`; Compose sets those to `/workspace/backups` and `/workspace/db/create_backup.sh`.

Emergency restore is intentionally a shell operation for now:

```sh
docker compose stop central_api central_web central_db_backup
docker compose run --rm central_db_backup sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists --no-owner "/backups/<backup-file>.dump"'
docker compose up -d
```

## Production Checks

`APP_ENV=production` fails startup when `SESSION_KEY`, `POSTGRES_PASSWORD`, or `PUBLIC_URL` still use local/default values. Keep `PUBLIC_URL` to the scheme and host only, put the ingress path in `APP_BASE_PATH`, and leave `VITE_APP_BASE_PATH` and `VITE_API_BASE_URL` blank unless you intentionally need frontend-specific overrides.
