#!/bin/sh
set -eu

cd "$(dirname "$0")"

REQ_HASH="$(sha256sum requirements.txt pyproject.toml | sha256sum | awk '{print $1}')"
DIGEST_FILE=".venv-requirements.sha256"

if [ ! -d venv ]; then
  python3 -m venv venv
fi

python_bin="${PYTHON_BIN:-./venv/bin/python}"

if [ ! -f "${DIGEST_FILE}" ] || [ "${REQ_HASH}" != "$(cat "${DIGEST_FILE}")" ]; then
  "$python_bin" -m pip install -r requirements.txt
  printf '%s\n' "${REQ_HASH}" > "${DIGEST_FILE}"
fi

"$python_bin" -m mypy app tests
"$python_bin" -m flake8 app tests
"$python_bin" -m ruff check app tests
"$python_bin" -m ruff format --check app tests
