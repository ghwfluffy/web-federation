#!/bin/sh
set -eu
python_bin="${PYTHON_BIN:-./venv/bin/python}"

"$python_bin" -m ruff check app tests
"$python_bin" -m mypy app
