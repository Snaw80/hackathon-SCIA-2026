#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --locked
npm --prefix web ci --no-audit --no-fund
uv run uvicorn meltdown.api:app --app-dir backend --host 127.0.0.1 --port 8000 &
meltdown_api_pid=$!
cleanup() {
  kill "$meltdown_api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
npm --prefix web run dev
