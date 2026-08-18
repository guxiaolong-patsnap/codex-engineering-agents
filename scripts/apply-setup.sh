#!/usr/bin/env bash
# Materialize agents + write automation spec (+ sync ~/.codex/automations).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT=""
SKIP_SYNC=0

usage() {
  echo "Usage: ./apply-setup.sh --project <dir> [--skip-codex-sync]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --skip-codex-sync) SKIP_SYNC=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$PROJECT" ]] || { usage; exit 1; }
PROJECT="$(cd "$PROJECT" && pwd)"

bash "$ROOT/scripts/ensure-project-agents.sh" --project "$PROJECT"

SYNC_ARGS=()
[[ "$SKIP_SYNC" -eq 1 ]] && SYNC_ARGS+=(--skip-codex-sync)
python3 "$ROOT/scripts/apply-setup.py" --project "$PROJECT" "${SYNC_ARGS[@]}"

echo "OK: setup applied for $PROJECT"
