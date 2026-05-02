# Auth Site

| | |
|---|---|
| [<img src="./web/public/auth-large.png" width="300"/>](./web/public/auth-large.png) | **Auth Site** is the central identity and directory application for a family of web apps.<br><br>It owns account sign-in, registration, password changes, profile details, profile images, user administration, registration codes, OAuth/OIDC identity, and the authenticated directory that links users to connected apps. |

## What It Provides

- A configurable login and registration site, served under `/auth` by default.
- Central user management for administrators.
- Registration-code creation and lifecycle management.
- User profile editing, password changes, and profile image hosting.
- OAuth Authorization Code with PKCE for apps that choose to delegate identity here.
- A signed-in directory landing page with launch links for connected apps.
- Operational basics including database backups, audit events, production config checks, and deployment-path aware cookies.

## Deployment Shape

The app is built as a small Docker Compose stack:

- FastAPI backend
- Vue frontend
- PostgreSQL database
- Nginx ingress/static frontend
- PostgreSQL backup worker

The default public base path is `/auth`, but it is configuration, not a hard-coded product assumption. Backend URLs, frontend routes, cookies, OAuth issuer metadata, redirect URLs, avatar URLs, and proxy behavior should derive from the configured base path.

## Local Development

Copy `.env.example` to `.env`, adjust values if needed, then run:

```sh
docker compose up --build
```

With default settings:

- App: `http://localhost:8190/auth`
- API status: `http://localhost:8190/auth/api/v1/status`
- Vite dev server: `http://localhost:8191/auth`

## Documentation

- Architecture overview: [`docs/architecture/README.md`](./docs/architecture/README.md)
- Local development and operations: [`docs/development.md`](./docs/development.md)
- Base-path deployment notes: [`docs/architecture/base-path-and-deployment.md`](./docs/architecture/base-path-and-deployment.md)
- OAuth behavior: [`docs/architecture/auth-oauth.md`](./docs/architecture/auth-oauth.md)
- Data model: [`docs/architecture/data-model.md`](./docs/architecture/data-model.md)
- Site directory: [`docs/architecture/site-directory.md`](./docs/architecture/site-directory.md)

## Validation

Run the full local validation script before considering changes complete:

```sh
./scripts/validate.sh
```
