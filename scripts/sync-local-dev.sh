#!/usr/bin/env bash
# Sync plugin agents into this repo's .codex/agents/ for local control-plane dev (./eng).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/plugins/engineering-agents/agents"
DST="$ROOT/.codex/agents"

mkdir -p "$DST"
cp "$SRC"/*.toml "$DST/"
echo "Synced plugin agents → $DST"
ls -1 "$DST"
