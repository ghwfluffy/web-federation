# Agent Instructions

Read these first:

- `docs/architecture/README.md`
- `docs/development.md`
- `docs/project-standards/README.md` when present

Keep `/auth` configurable. Do not hard-code it into routes, cookies, OAuth metadata, redirects, avatar URLs, or frontend links. Keep identity behavior owned here: login, registration, users, registration codes, profile, password, avatar, OAuth, and the app directory.

## Validation

- Full repo: `./scripts/validate.sh`
- Backend tests: `cd api && ./test.sh`
- Backend lint/type checks: `cd api && ./lint.sh`
- Frontend tests/type checks: `cd web && ./test.sh`
- Frontend production build: `cd web && npm run build`
- Compose/config changes: `docker compose config`

For doc-only changes, checking the edited Markdown is sufficient. Do not commit generated output such as virtualenvs, `node_modules`, build artifacts, backups, or local `.env` secrets.
