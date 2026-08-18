#!/usr/bin/env bash
# Sync eng-agents subagents to ~/.codex/agents (run once after plugin install).
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/sync-agents.sh" "$@"
