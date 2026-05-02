#!/bin/bash

set -eux -o pipefail

(
    cd web
    ./build.sh
)

(
    cd api
    ./lint.sh
)

docker compose build
docker compose down
docker compose up -d
docker compose logs -f
