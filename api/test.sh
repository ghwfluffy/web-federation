#!/bin/sh
set -eu
python_bin="${PYTHON_BIN:-./venv/bin/python}"

"$python_bin" -m pytest
