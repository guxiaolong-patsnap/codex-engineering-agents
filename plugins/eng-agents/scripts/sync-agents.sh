#!/usr/bin/env bash
# Sync managed agents to ~/.codex/agents
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
MANIFEST="$ROOT/config/managed-manifest.json"
TARGET="$CODEX_HOME/agents"

mkdir -p "$TARGET"
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }

VERSION="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['version'])")"
AGENTS="$(python3 -c "import json;print('\n'.join(json.load(open('$MANIFEST'))['managed_agents']))")"
BEGIN="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['managed_agents_marker']['begin'])")"
END="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['managed_agents_marker']['end'])")"

echo "eng-agents $VERSION → $TARGET"
for f in $AGENTS; do
  cp "$ROOT/agents/$f" "$TARGET/$f"
  echo "  + $f"
done

python3 - "$CODEX_HOME/AGENTS.md" "$ROOT/config/AGENTS.managed.md" "$BEGIN" "$END" <<'PY'
import pathlib, sys
target = pathlib.Path(sys.argv[1])
src = pathlib.Path(sys.argv[2])
begin, end = sys.argv[3], sys.argv[4]
block = f"{begin}\n{src.read_text().rstrip()}\n{end}\n"
text = target.read_text() if target.exists() else ""
if begin in text and end in text:
    pre, post = text.split(begin, 1)[0], text.split(end, 1)[1]
    text = pre + block + (post[1:] if post.startswith("\n") else post)
else:
    text = (text + "\n" if text and not text.endswith("\n") else text) + block
target.write_text(text)
print(f"  updated {target}")
PY

echo "Done. Ensure ~/.codex/config.toml enables multi_agent_v2 and agents."
