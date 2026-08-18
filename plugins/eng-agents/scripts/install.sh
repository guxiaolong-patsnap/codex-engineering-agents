#!/usr/bin/env bash
# Plugin install / upgrade: sync managed agents to ~/.codex/agents.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "$ROOT/scripts/sync-agents.sh" "$ROOT/scripts/install-project.sh"
"$ROOT/scripts/sync-agents.sh"

cat <<EOF

Plugin eng-agents ready.

Install via PatSnap marketplace:
  codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
  codex plugin add eng-agents@patsnap-openai-plugins

Skills: \$issue-pipeline, \$security-review, \$project-install

Project-scoped install (team via git):
  bash $ROOT/scripts/install-project.sh --into /path/to/repo

EOF
