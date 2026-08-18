#!/usr/bin/env bash
# Project-level installer for codex-engineering-agents.
# Inspired by https://github.com/sehoon787/my-codex (install.sh UX),
# but installs into <project>/.codex/ — NOT ~/.codex/ (personal).
#
# Usage:
#   ./install.sh --into /path/to/business-git-repo
#   cd /path/to/business-git-repo && curl -fsSL <raw>/install.sh | bash -s -- --into .
#
# Or from a clone of this repo:
#   bash install.sh --into ~/code/my-app
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
VERSION="0.1.0"
INTO=""
FORCE=0
DRY_RUN=0

BOOTSTRAP_REPO="${ENG_AGENTS_BOOTSTRAP_REPO:-https://github.com/guxiaolong-patsnap/codex-engineering-agents.git}"

usage() {
  cat <<EOF
Usage:
  ./install.sh --into <project-dir> [--force] [--dry-run]

Installs project-scoped Codex agents into:
  <project-dir>/.codex/agents/*.toml
  <project-dir>/.codex/config.toml          (merged / created)
  <project-dir>/AGENTS.md                  (managed block upsert)
  <project-dir>/.codex/.eng-agents-manifest.json

This is PROJECT-level (like vendoring agents into a git repo).
It does NOT write to ~/.codex/agents (personal / my-codex style).

Examples:
  ./install.sh --into ~/code/my-app
  cd ~/code/my-app && bash /path/to/codex-engineering-agents/install.sh --into .
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

bootstrap_if_needed() {
  if [[ -f "$REPO_ROOT/.codex/agents/coding.toml" && -f "$REPO_ROOT/.codex/agents/security.toml" ]]; then
    return 0
  fi
  echo "[bootstrap] Not a full checkout; cloning $BOOTSTRAP_REPO ..."
  local tmp
  tmp="$(mktemp -d)"
  git clone --depth 1 "$BOOTSTRAP_REPO" "$tmp/eng-agents"
  bash "$tmp/eng-agents/install.sh" --into "${INTO:-.}" ${FORCE:+--force} ${DRY_RUN:+--dry-run}
  local st=$?
  rm -rf "$tmp"
  exit "$st"
}

if [[ -z "$INTO" ]]; then
  usage
  exit 1
fi

bootstrap_if_needed

INTO="$(cd "$INTO" && pwd)"
TARGET_CODEX="$INTO/.codex"
TARGET_AGENTS="$TARGET_CODEX/agents"
MANIFEST="$TARGET_CODEX/.eng-agents-manifest.json"
SRC_AGENTS="$REPO_ROOT/.codex/agents"
SRC_CONFIG="$REPO_ROOT/.codex/config.toml"
SRC_AGENTS_MD="$REPO_ROOT/AGENTS.md"
BEGIN="<!-- BEGIN ENG-AGENTS MANAGED -->"
END="<!-- END ENG-AGENTS MANAGED -->"

if [[ ! -d "$INTO/.git" && "$FORCE" -ne 1 ]]; then
  echo "Refusing: $INTO is not a git repo (pass --force to override)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 required" >&2
  exit 1
fi

echo "=== eng-agents project installer ==="
echo "Source:  $REPO_ROOT (v$VERSION)"
echo "Target:  $INTO/.codex/   (project-scoped)"
echo "Personal ~/.codex/agents will NOT be modified."
echo

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would install:"
  ls -1 "$SRC_AGENTS"/*.toml
  exit 0
fi

mkdir -p "$TARGET_AGENTS"

# Remove only previously managed agent files (manifest-based, like my-codex)
if [[ -f "$MANIFEST" ]]; then
  echo "[1/4] Cleaning previous eng-agents-managed files (manifest only)..."
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
  echo "[1/4] No previous manifest — skip stale cleanup"
fi

echo "[2/4] Installing agents into $TARGET_AGENTS ..."
INSTALLED=()
for src in "$SRC_AGENTS"/*.toml; do
  base="$(basename "$src")"
  cp "$src" "$TARGET_AGENTS/$base"
  INSTALLED+=(".codex/agents/$base")
  echo "  + .codex/agents/$base"
done

echo "[3/4] Writing .codex/config.toml (project) ..."
# If target has config, ensure multi_agent keys exist; else copy ours
if [[ -f "$TARGET_CODEX/config.toml" ]]; then
  python3 - "$TARGET_CODEX/config.toml" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
needed = [
    ("[features]", "\n[features]\nmulti_agent_v2 = true\n"),
    ("multi_agent_v2", None),
    ("[agents]", "\n[agents]\nenabled = true\nmax_threads = 6\nmax_depth = 1\ninterrupt_message = true\n"),
    ("enabled = true", None),
]
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

echo "[4/4] Upserting managed AGENTS.md block ..."
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
root = manifest_path.parent.parent  # project root
hashes = {}
for rel in files:
    p = root / rel
    if p.is_file():
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
state = {
    "package": "codex-engineering-agents",
    "scope": "project",
    "version": version,
    "files": files,
    "sha256": hashes,
}
manifest_path.write_text(json.dumps(state, indent=2) + "\n")
print(f"wrote {manifest_path}")
PY

cat <<EOF

Install OK (project-scoped).

Next:
  cd $INTO
  codex
  # Trust this project when prompted
  # Then: Spawn coding to … / Spawn security to …

Re-install / upgrade later (only replaces managed files):
  bash $REPO_ROOT/install.sh --into $INTO

Note: This did not touch ~/.codex/agents (personal). That is intentional.
EOF
