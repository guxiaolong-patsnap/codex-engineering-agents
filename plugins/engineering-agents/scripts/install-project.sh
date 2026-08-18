#!/usr/bin/env bash
# Project-level installer — writes to <project>/.codex/, NOT ~/.codex/agents.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST_JSON="$ROOT/config/managed-manifest.json"
VERSION="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['version'])" 2>/dev/null || echo "0.2.0")"
BEGIN="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['managed_agents_marker']['begin'])" 2>/dev/null || echo '<!-- BEGIN ENGINEERING-AGENTS MANAGED -->')"
END="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON'))['managed_agents_marker']['end'])" 2>/dev/null || echo '<!-- END ENGINEERING-AGENTS MANAGED -->')"
PROJECT_MANIFEST_NAME="$(python3 -c "import json; print(json.load(open('$MANIFEST_JSON')).get('project_manifest_filename', '.engineering-agents-manifest.json'))" 2>/dev/null || echo '.engineering-agents-manifest.json')"

INTO=""
FORCE=0
DRY_RUN=0

usage() {
  cat <<EOF
Usage:
  ./install-project.sh --into <project-dir> [--force] [--dry-run]

Installs project-scoped Codex agents into:
  <project-dir>/.codex/agents/*.toml
  <project-dir>/.codex/config.toml
  <project-dir>/AGENTS.md (managed block)
  <project-dir>/.codex/$PROJECT_MANIFEST_NAME

Does NOT modify ~/.codex/agents.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --into) INTO="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$INTO" ]]; then
  usage
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 required" >&2
  exit 1
fi

INTO="$(cd "$INTO" && pwd)"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would install from $ROOT/agents into $INTO/.codex/"
  ls -1 "$ROOT/agents"/*.toml
  exit 0
fi

if [[ ! -d "$INTO/.git" && "$FORCE" -ne 1 ]]; then
  echo "Refusing: $INTO is not a git repo (pass --force to override)." >&2
  exit 1
fi

TARGET_CODEX="$INTO/.codex"
TARGET_AGENTS="$TARGET_CODEX/agents"
MANIFEST="$TARGET_CODEX/$PROJECT_MANIFEST_NAME"
SRC_AGENTS="$ROOT/agents"
SRC_CONFIG="$ROOT/config/project-config.toml"
SRC_AGENTS_MD="$ROOT/config/AGENTS.managed.md"

echo "=== engineering-agents project install ==="
echo "Plugin:  $ROOT (v$VERSION)"
echo "Target:  $INTO/.codex/"
echo

mkdir -p "$TARGET_AGENTS"

if [[ -f "$MANIFEST" ]]; then
  echo "[1/4] Cleaning previous managed files (manifest)..."
  python3 - "$MANIFEST" "$INTO" <<'PY'
import json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
root = pathlib.Path(sys.argv[2])
for rel in manifest.get("files", []):
    p = root / rel
    if p.is_file():
        p.unlink()
        print(f"  removed {rel}")
PY
else
  echo "[1/4] No previous manifest — skip cleanup"
fi

echo "[2/4] Installing agents..."
INSTALLED=()
for src in "$SRC_AGENTS"/*.toml; do
  base="$(basename "$src")"
  cp "$src" "$TARGET_AGENTS/$base"
  INSTALLED+=(".codex/agents/$base")
  echo "  + .codex/agents/$base"
done

echo "[3/4] Writing .codex/config.toml ..."
if [[ -f "$TARGET_CODEX/config.toml" ]]; then
  python3 - "$TARGET_CODEX/config.toml" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
out = text
if "[features]" not in out:
    out += "\n[features]\nmulti_agent_v2 = true\n"
elif "multi_agent_v2" not in out:
    out = out.replace("[features]", "[features]\nmulti_agent_v2 = true", 1)
if "[agents]" not in out:
    out += "\n[agents]\nenabled = true\nmax_threads = 6\nmax_depth = 1\ninterrupt_message = true\n"
elif "enabled" not in out.split("[agents]", 1)[-1].split("[", 1)[0]:
    out = out.replace("[agents]", "[agents]\nenabled = true", 1)
p.write_text(out if out.endswith("\n") else out + "\n")
print("  merged existing .codex/config.toml")
PY
else
  cp "$SRC_CONFIG" "$TARGET_CODEX/config.toml"
  echo "  wrote .codex/config.toml"
fi
INSTALLED+=(".codex/config.toml")

echo "[4/4] Upserting AGENTS.md managed block..."
python3 - "$INTO/AGENTS.md" "$SRC_AGENTS_MD" "$BEGIN" "$END" <<'PY'
import pathlib, sys
target = pathlib.Path(sys.argv[1])
src = pathlib.Path(sys.argv[2])
begin, end = sys.argv[3], sys.argv[4]
body = src.read_text().rstrip()
block = f"{begin}\n{body}\n{end}\n"
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
print(f"  updated {target}")
PY
INSTALLED+=("AGENTS.md")

python3 - "$MANIFEST" "$VERSION" "${INSTALLED[@]}" <<'PY'
import hashlib, json, pathlib, sys
manifest_path = pathlib.Path(sys.argv[1])
version = sys.argv[2]
files = sys.argv[3:]
root = manifest_path.parent.parent
hashes = {}
for rel in files:
    p = root / rel
    if p.is_file():
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
state = {
    "package": "engineering-agents",
    "scope": "project",
    "version": version,
    "files": files,
    "sha256": hashes,
}
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(state, indent=2) + "\n")
print(f"wrote {manifest_path}")
PY

cat <<EOF

Project install OK.

Next:
  cd $INTO
  codex
  # Trust this project
  # Spawn coding to … / Spawn security to …
  # Or use plugin skills: \$issue-pipeline / \$security-review

Commit .codex/ + AGENTS.md so teammates share the same agents.
EOF
