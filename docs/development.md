# Development

## Local Defaults

Copy `.env.example` to `.env` and adjust values as needed. The default external base path is `/auth`.

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

The frontend portion runs only when `web/node_modules` exists.

## Backups

Automatic backups run through the `db-backup` Compose service and write dump files plus JSON manifests under `./backups`.

Admins can list manifests and trigger a manual backup through `/api/v1/admin/backups`. The API container needs `pg_dump`, `BACKUP_DIR`, and `BACKUP_SCRIPT_PATH`; Compose sets those to `/workspace/backups` and `/workspace/db/create_backup.sh`.

Emergency restore is intentionally a shell operation for now:

```sh
docker compose stop api web db-backup
docker compose run --rm db-backup sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists --no-owner "/backups/<backup-file>.dump"'
docker compose up -d
```

## Production Checks

`APP_ENV=production` fails startup when `SESSION_KEY`, `POSTGRES_PASSWORD`, or `PUBLIC_URL` still use local/default values. Use an explicit `SESSION_COOKIE_NAME` and leave `APP_BASE_PATH`, `VITE_APP_BASE_PATH`, and `VITE_API_BASE_URL` aligned.
