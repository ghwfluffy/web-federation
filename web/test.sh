#!/bin/sh
set -eu

cd "$(dirname "$0")"

if [ -f ../.env ]; then
  set -a
  . ../.env
  set +a
fi

DIGEST_SOURCE="package-lock.json"
if [ ! -f "${DIGEST_SOURCE}" ]; then
  DIGEST_SOURCE="package.json"
fi

REQ_HASH="$(sha256sum "${DIGEST_SOURCE}" | sha256sum | awk '{print $1}')"
DIGEST_FILE=".node-deps.sha256"

if [ ! -d node_modules ] || [ ! -f "${DIGEST_FILE}" ] || [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  npm install
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

npm run typecheck
npm test
