#!/usr/bin/env bash
# Thin wrapper: project-level install via engineering-agents plugin script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_INSTALL="$SCRIPT_DIR/plugins/engineering-agents/scripts/install-project.sh"
BOOTSTRAP_REPO="${ENGINEERING_AGENTS_BOOTSTRAP_REPO:-${ENG_AGENTS_BOOTSTRAP_REPO:-https://github.com/guxiaolong-patsnap/codex-engineering-agents.git}}"

if [[ ! -f "$PLUGIN_INSTALL" ]]; then
  echo "[bootstrap] Not a full checkout; cloning $BOOTSTRAP_REPO ..."
  tmp="$(mktemp -d)"
  git clone --depth 1 "$BOOTSTRAP_REPO" "$tmp/eng-agents"
  exec bash "$tmp/eng-agents/install.sh" "$@"
fi

exec bash "$PLUGIN_INSTALL" "$@"
