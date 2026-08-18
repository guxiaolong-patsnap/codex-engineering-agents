#!/usr/bin/env python3
"""Apply eng-agents setup: write automation spec and sync to ~/.codex/automations/."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

DEFAULT_PROMPT = """\
You are the Engineering Agents supervisor for this Codex execution project.

1. Read `.git_projects.json` in the project root.
2. For each enabled repo entry, use its local `path` (mount with --add-dir if needed).
3. Fetch open issues from GitLab or GitHub using the token env vars named in credentials.
4. Pick at most one issue that matches a routing rule (labels or keywords).
5. For the matched rule:
   - If pipeline is `issue-pipeline`, run `$issue-pipeline` for that issue.
   - Otherwise spawn the listed agents in order (e.g. Spawn coding to …, then Spawn security to …).
6. Do not merge or force-push. Summarize actions and blockers.
7. Append a one-line run record to `.codex/runs/issue-poll.ndjson` if the directory exists.
"""


def load_git_projects(project: pathlib.Path) -> dict:
    path = project / ".git_projects.json"
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Save setup in the HTML UI first.")
    return json.loads(path.read_text())


def build_automation_spec(project: pathlib.Path, cfg: dict) -> dict:
    auto = cfg.get("automation") or {}
    interval = int(auto.get("interval_minutes") or 10)
    enabled = bool(auto.get("enabled", True))
    name = auto.get("name") or "Engineering Agents — issue poll"
    model = auto.get("model") or "gpt-5.4"
    return {
        "version": 1,
        "id": "eng-agents-issue-poll",
        "enabled": enabled,
        "name": name,
        "description": "Poll bound git repos for issues and route to sub-agents per .git_projects.json routing rules.",
        "prompt": DEFAULT_PROMPT.strip(),
        "schedule": {
            "interval_minutes": interval,
            "rrule": f"RRULE:FREQ=MINUTELY;INTERVAL={interval}",
        },
        "model": model,
        "execution_environment": "local",
        "project_path": str(project.resolve()),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def write_automation_spec(project: pathlib.Path, spec: dict) -> pathlib.Path:
    dest_dir = project / ".codex" / "automations"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "eng-agents.json"
    dest.write_text(json.dumps(spec, indent=2) + "\n")
    return dest


def sync_codex_automation(spec: dict, codex_home: pathlib.Path) -> pathlib.Path:
    auto_id = spec["id"]
    dest_dir = codex_home / "automations" / auto_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "automation.toml"

    status = "ACTIVE" if spec.get("enabled", True) else "PAUSED"
    rrule = spec["schedule"]["rrule"]
    project_path = spec.get("project_path") or "."
    prompt = spec["prompt"].replace('"""', '\\"""')
    name = spec["name"].replace('"', '\\"')

    body = f'''version = 1
id = "{auto_id}"
kind = "cron"
name = "{name}"
prompt = """
{prompt}
"""
status = "{status}"
rrule = "{rrule}"
model = "{spec.get("model", "gpt-5.4")}"
execution_environment = "{spec.get("execution_environment", "local")}"
target = {{ type = "local" }}
cwds = ["{project_path}"]
'''
    dest.write_text(body)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply eng-agents automation spec")
    parser.add_argument("--project", required=True, help="Codex execution project directory")
    parser.add_argument(
        "--codex-home",
        default=str(pathlib.Path.home() / ".codex"),
        help="Codex home (default: ~/.codex)",
    )
    parser.add_argument(
        "--skip-codex-sync",
        action="store_true",
        help="Only write project spec, do not sync to ~/.codex/automations",
    )
    args = parser.parse_args()

    project = pathlib.Path(args.project).resolve()
    cfg = load_git_projects(project)
    spec = build_automation_spec(project, cfg)
    spec_path = write_automation_spec(project, spec)
    print(f"wrote {spec_path}")

    if not args.skip_codex_sync:
        codex_home = pathlib.Path(args.codex_home).expanduser()
        toml_path = sync_codex_automation(spec, codex_home)
        print(f"synced {toml_path}")
        print("Confirm in Codex App → Automations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
