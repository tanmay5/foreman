#!/usr/bin/env bash
# Bootstrap a Foreman dev environment from scratch.
# Usage: ./scripts/bootstrap.sh

set -euo pipefail

# 1. Ensure uv is installed (modern Python package manager).
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/"
    echo "Quick: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 2. Sync dependencies into a venv managed by uv.
uv sync --extra dev

# 3. Copy .env.example -> .env if it doesn't exist.
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Fill in your secrets before running 'foreman run'."
fi

echo
echo "Foreman dev environment ready."
echo "Next: edit .env, then run 'uv run foreman doctor' to verify connectors."
