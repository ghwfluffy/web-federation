#!/bin/sh
set -eu

(cd api && ./test.sh)

if [ -d web/node_modules ]; then
  (cd web && npm run typecheck && npm test)
else
  printf '%s\n' "Skipping frontend validation because web/node_modules is not installed."
fi
