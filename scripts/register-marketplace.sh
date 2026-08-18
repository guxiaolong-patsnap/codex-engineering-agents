#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found" >&2
  exit 1
fi

codex plugin marketplace add "$ROOT"
echo
codex plugin marketplace list || true
echo
codex plugin list || true
echo
echo "Install/enable plugin:"
echo "  codex plugin add eng-agent-team@codex-engineering-agents"
