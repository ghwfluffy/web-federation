# Development

## Local Defaults

Copy `.env.example` to `.env` and adjust values as needed. The default external base path is `/auth`.

```sh
docker compose up --build
```

With the defaults:

- Frontend through Nginx: `http://localhost:8090/auth`
- API status through Nginx: `http://localhost:8090/auth/api/v1/status`
- Vite dev server: `http://localhost:8081/auth`

## Validation

```sh
./scripts/validate.sh
```

The frontend portion runs only when `web/node_modules` exists.
