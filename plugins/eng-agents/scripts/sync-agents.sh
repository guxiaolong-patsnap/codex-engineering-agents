#!/usr/bin/env bash
# Sync managed agent TOML + AGENTS.md block into Codex home (~/.codex/agents).
# Plugin install entry — personal scope (default plugin distribution).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
ENG_AGENTS_HOME="${ENG_AGENTS_HOME:-${ENGINEERING_AGENTS_HOME:-${ENG_AGENT_TEAM_HOME:-$HOME/.eng-agents}}}"
MANIFEST="$ROOT/config/managed-manifest.json"
AGENTS_SRC="$ROOT/config/AGENTS.managed.md"
AGENTS_DIR="$ROOT/agents"
TARGET_AGENTS="$CODEX_HOME/agents"
TARGET_AGENTS_MD="$CODEX_HOME/AGENTS.md"
SYNC_STATE="$ENG_AGENTS_HOME/sync-state.json"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$TARGET_AGENTS" "$ENG_AGENTS_HOME/backups"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 required for sync" >&2
  exit 1
fi

VERSION="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['version'])")"
FILES="$(python3 -c "import json;print('\n'.join(json.load(open('$MANIFEST'))['managed_agents']))")"
BEGIN="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['managed_agents_marker']['begin'])")"
END="$(python3 -c "import json;print(json.load(open('$MANIFEST'))['managed_agents_marker']['end'])")"

echo "Syncing eng-agents $VERSION → $TARGET_AGENTS (state: $ENG_AGENTS_HOME)"

synced=()
for f in $FILES; do
  src="$AGENTS_DIR/$f"
  dst="$TARGET_AGENTS/$f"
  if [[ ! -f "$src" ]]; then
    echo "missing managed agent: $src" >&2
    exit 1
  fi
  if [[ -f "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "unchanged: $f"
      synced+=("$f")
      continue
    fi
    cp "$dst" "$ENG_AGENTS_HOME/backups/${f}.bak.$TS"
    echo "backup: $f → backups/${f}.bak.$TS"
  fi
  cp "$src" "$dst"
  echo "installed: $f"
  synced+=("$f")
done

python3 - "$TARGET_AGENTS_MD" "$AGENTS_SRC" "$BEGIN" "$END" <<'PY'
import pathlib, sys
target = pathlib.Path(sys.argv[1])
src = pathlib.Path(sys.argv[2])
begin, end = sys.argv[3], sys.argv[4]
body = src.read_text()
block = f"{begin}\n{body.rstrip()}\n{end}\n"
if target.exists():
    text = target.read_text()
    if begin in text and end in text:
        pre = text.split(begin, 1)[0]
        post = text.split(end, 1)[1]
        if post.startswith("\n"):
            post = post[1:]
        text = pre + block + post
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block
else:
    text = block
target.write_text(text)
print(f"updated: {target}")
PY

python3 - "$SYNC_STATE" "$VERSION" "$TARGET_AGENTS" "$FILES" "$TS" <<'PY'
import hashlib, json, pathlib, sys
state_path = pathlib.Path(sys.argv[1])
version = sys.argv[2]
agents_dir = pathlib.Path(sys.argv[3])
files = sys.argv[4].split()
ts = sys.argv[5]
hashes = {}
for f in files:
    data = (agents_dir / f).read_bytes()
    hashes[f] = hashlib.sha256(data).hexdigest()
state = {
    "plugin": "eng-agents",
    "host": "codex",
    "scope": "personal",
    "version": version,
    "synced_at": ts,
    "agents_dir": str(agents_dir),
    "files": hashes,
}
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, indent=2) + "\n")
print(f"wrote: {state_path}")
PY

echo
echo "Personal sync OK. Enable multi-agent in ~/.codex/config.toml if needed:"
echo "  [features]"
echo "  multi_agent_v2 = true"
echo "  [agents]"
echo "  enabled = true"
echo
echo "For project-scoped install (team via git):"
echo "  bash $ROOT/scripts/install-project.sh --into /path/to/repo"
