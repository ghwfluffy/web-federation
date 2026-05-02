# Base Path And Deployment

## Default

The default external base path is `/auth`.

## Required Configuration

- `APP_BASE_PATH`: backend and Nginx route prefix.
- `VITE_APP_BASE_PATH`: Vue Router and built asset base.
- `VITE_API_BASE_URL`: frontend API root, normally `${APP_BASE_PATH}/api/v1`.
- `PUBLIC_URL`: scheme and host only, without the base path.

## Rule

Do not hard-code `/auth` into application behavior. It is the default value only. Deployments may change the base path by setting the variables above.
