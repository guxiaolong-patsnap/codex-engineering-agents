#!/usr/bin/env bash
# Sync canonical agents from this repo's .codex/agents/ into another Codex project.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST_JSON="$ROOT/config/managed-manifest.json"
VERSION="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['version'])" 2>/dev/null || echo "0.5.0")"
BEGIN="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['managed_agents_marker']['begin'])" 2>/dev/null || echo '<!-- BEGIN ENG-AGENTS MANAGED -->')"
END="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['managed_agents_marker']['end'])" 2>/dev/null || echo '<!-- END ENG-AGENTS MANAGED -->')"
PROJECT_MANIFEST_NAME="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON')).get('project_manifest_filename', '.eng-agents-manifest.json'))" 2>/dev/null || echo '.eng-agents-manifest.json')"

PROJECT=""
DRY_RUN=0

usage() {
  echo "Usage: ./ensure-project-agents.sh --project <dir> [--dry-run]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$PROJECT" ]] || { usage; exit 1; }
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }

PROJECT="$(cd "$PROJECT" && pwd)"
SRC_AGENTS="$ROOT/.codex/agents"
SRC_CONFIG="$ROOT/.codex/config.toml"
SRC_AGENTS_MD="$ROOT/AGENTS.md"

if [[ ! -d "$SRC_AGENTS" ]]; then
  echo "Missing source agents: $SRC_AGENTS" >&2
  exit 1
fi

if [[ "$PROJECT" == "$ROOT" ]]; then
  echo "OK: this repo is the project; agents already at $SRC_AGENTS"
  exit 0
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] copy $SRC_AGENTS → $PROJECT/.codex/agents/"
  ls -1 "$SRC_AGENTS"/*.toml
  exit 0
fi

TARGET_CODEX="$PROJECT/.codex"
TARGET_AGENTS="$TARGET_CODEX/agents"
MANIFEST="$TARGET_CODEX/$PROJECT_MANIFEST_NAME"

echo "=== eng-agents → $PROJECT ==="
mkdir -p "$TARGET_AGENTS"

if [[ -f "$MANIFEST" ]]; then
  python3 - "$MANIFEST" "$PROJECT" <<'PY'
import json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
root = pathlib.Path(sys.argv[2])
for rel in manifest.get("files", []):
    p = root / rel
    if p.is_file():
        p.unlink()
        print(f"  removed {rel}")
PY
fi

INSTALLED=()
for src in "$SRC_AGENTS"/*.toml; do
  base="$(basename "$src")"
  cp "$src" "$TARGET_AGENTS/$base"
  INSTALLED+=(".codex/agents/$base")
  echo "  + .codex/agents/$base"
done

if [[ -f "$TARGET_CODEX/config.toml" ]]; then
  python3 - "$TARGET_CODEX/config.toml" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
out = p.read_text()
if "[features]" not in out:
    out += "\n[features]\nmulti_agent_v2 = true\n"
elif "multi_agent_v2" not in out:
    out = out.replace("[features]", "[features]\nmulti_agent_v2 = true", 1)
if "[agents]" not in out:
    out += "\n[agents]\nenabled = true\nmax_threads = 6\nmax_depth = 1\ninterrupt_message = true\n"
elif "enabled" not in out.split("[agents]", 1)[-1].split("[", 1)[0]:
    out = out.replace("[agents]", "[agents]\nenabled = true", 1)
p.write_text(out if out.endswith("\n") else out + "\n")
print("  merged .codex/config.toml")
PY
else
  cp "$SRC_CONFIG" "$TARGET_CODEX/config.toml"
  echo "  + .codex/config.toml"
fi
INSTALLED+=(".codex/config.toml")

python3 - "$PROJECT/AGENTS.md" "$SRC_AGENTS_MD" "$BEGIN" "$END" <<'PY'
import pathlib, sys
target = pathlib.Path(sys.argv[1])
src = pathlib.Path(sys.argv[2])
begin, end = sys.argv[3], sys.argv[4]
body = src.read_text().rstrip()
# strip existing managed markers from source body if present
if begin in body and end in body:
    body = body.split(begin, 1)[1].split(end, 1)[0].strip()
block = f"{begin}\n{body}\n{end}\n"
if target.exists():
    text = target.read_text()
    if begin in text and end in text:
        pre, post = text.split(begin, 1)[0], text.split(end, 1)[1]
        text = pre + block + (post[1:] if post.startswith("\n") else post)
    else:
        text = (text + "\n" if text and not text.endswith("\n") else text) + "\n" + block
else:
    text = block
target.write_text(text)
print(f"  updated {target}")
PY
INSTALLED+=("AGENTS.md")

python3 - "$MANIFEST" "$VERSION" "${INSTALLED[@]}" <<'PY'
import hashlib, json, pathlib, sys
manifest_path = pathlib.Path(sys.argv[1])
version = sys.argv[2]
files = sys.argv[3:]
root = manifest_path.parent.parent
hashes = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
          for rel in files if (root / rel).is_file()}
manifest_path.write_text(json.dumps({
    "package": "eng-agents",
    "scope": "project",
    "version": version,
    "files": files,
    "sha256": hashes,
}, indent=2) + "\n")
print(f"wrote {manifest_path}")
PY

echo "OK: agents in $PROJECT/.codex/agents/"
