#!/usr/bin/env bash

set -euo pipefail

python -m venv ".venv"

./.venv/bin/pip install -e .[dev]
