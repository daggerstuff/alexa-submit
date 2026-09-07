#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${MCP_HOST:-127.0.0.1}"
PORT="${MCP_PORT:-8001}"
PATH_VALUE="${MCP_PATH:-/mcp}"
ALLOWED_HOSTS="${MCP_ALLOWED_HOSTS:-${HOST}:*,localhost:*}"
ALLOWED_ORIGINS="${MCP_ALLOWED_ORIGINS:-http://127.0.0.1:*,http://localhost:*}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export MCP_HOST="$HOST"
export MCP_PORT="$PORT"
export MCP_PATH="$PATH_VALUE"
export MCP_ALLOWED_HOSTS="$ALLOWED_HOSTS"
export MCP_ALLOWED_ORIGINS="$ALLOWED_ORIGINS"

exec python -m server.mcp_server
