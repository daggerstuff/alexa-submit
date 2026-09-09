#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Prefer uv for fast, pinned-Python environment creation; fall back to the
# stdlib venv module when uv is not installed. Reuse an existing .venv so
# re-running is quick and non-destructive.
if command -v uv >/dev/null 2>&1; then
  if [ -x .venv/bin/python ]; then
    echo "==> Reusing existing virtual environment at .venv"
  else
    echo "==> Creating virtual environment with uv (Python 3.13)"
    uv venv .venv --python 3.13
  fi
  echo "==> Installing dependencies with uv"
  uv pip install --python .venv/bin/python -r server/requirements.txt
else
  echo "==> uv not found; falling back to python3 -m venv"
  if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r server/requirements.txt
fi

cp -n .env.example .env 2>/dev/null || true

echo
echo "Initialized Alexa+ clinical simulation starter."
echo "Activate with:  source .venv/bin/activate"
echo "Run tests with: .venv/bin/python -m pytest -q"