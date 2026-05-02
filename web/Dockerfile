FROM node:22-slim AS build

WORKDIR /workspace/web

ARG VITE_APP_BASE_PATH=/auth
ARG VITE_API_BASE_URL=/auth/api/v1
ENV VITE_APP_BASE_PATH=$VITE_APP_BASE_PATH
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY web/package*.json ./
RUN npm install

COPY web/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY --from=build /workspace/web/dist /usr/share/nginx/html
