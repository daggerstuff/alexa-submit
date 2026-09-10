#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load .env if present so inference and API-key settings apply locally.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${MCP_HOST:-127.0.0.1}"
PORT="${MCP_PORT:-8001}"
PATH_VALUE="${MCP_PATH:-/mcp}"
ALLOWED_HOSTS="${MCP_ALLOWED_HOSTS:-${HOST}:*,localhost:*}"
ALLOWED_ORIGINS="${MCP_ALLOWED_ORIGINS:-http://127.0.0.1:*,http://localhost:*}"
API_KEY="${MCP_API_KEY:-}"
RATE_LIMIT="${MCP_RATE_LIMIT_REQUESTS:-0}"
RATE_WINDOW="${MCP_RATE_LIMIT_WINDOW_SECONDS:-60}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export MCP_HOST="$HOST"
export MCP_PORT="$PORT"
export MCP_PATH="$PATH_VALUE"
export MCP_ALLOWED_HOSTS="$ALLOWED_HOSTS"
export MCP_ALLOWED_ORIGINS="$ALLOWED_ORIGINS"
export MCP_API_KEY="$API_KEY"
export MCP_RATE_LIMIT_REQUESTS="$RATE_LIMIT"
export MCP_RATE_LIMIT_WINDOW_SECONDS="$RATE_WINDOW"

exec python -m server.mcp_server
