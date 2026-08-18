#!/usr/bin/env bash
# Open setup UI (local server → .git_projects.json).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT=""
PORT="${ENG_AGENTS_SETUP_PORT:-8765}"
HOST="127.0.0.1"

usage() {
  echo "Usage: ./open-setup-ui.sh [--project <dir>] [--port 8765]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

PROJECT="$(cd "${PROJECT:-.}" && pwd)"
URL="http://${HOST}:${PORT}/"

python3 "$ROOT/scripts/setup-server.py" --project "$PROJECT" --host "$HOST" --port "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
sleep 0.4

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
else
  echo "Open: $URL"
fi

echo "Setup UI: $URL  (project: $PROJECT)"
wait "$SERVER_PID"
