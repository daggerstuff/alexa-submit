#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

if command -v ngrok >/dev/null 2>&1; then
  exec ngrok http "$PORT"
fi

cat <<'MSG'
No supported tunnel binary was found.
Install and authenticate a tunnel provider such as ngrok, then rerun this script.
The public URL must be copied into alexa_config/skill.json and the Alexa developer console.
MSG
exit 1
