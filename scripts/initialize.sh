#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r server/requirements.txt
cp -n .env.example .env 2>/dev/null || true

echo "Initialized Alexa+ clinical simulation starter. Activate with: source .venv/bin/activate"
