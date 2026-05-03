FROM node:22-slim AS build

WORKDIR /workspace/web

ARG VITE_APP_BASE_PATH
ARG VITE_API_BASE_URL=
ARG API_V1_PREFIX
ARG VITE_API_PROXY_TARGET
ENV VITE_APP_BASE_PATH=$VITE_APP_BASE_PATH
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV API_V1_PREFIX=$API_V1_PREFIX
ENV VITE_API_PROXY_TARGET=$VITE_API_PROXY_TARGET

COPY web/package*.json ./
RUN npm install

COPY web/ ./
RUN npm run build

FROM nginx:1.29-alpine

COPY --from=build /workspace/web/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/10-normalize-app-base-path.envsh /docker-entrypoint.d/10-normalize-app-base-path.envsh
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
