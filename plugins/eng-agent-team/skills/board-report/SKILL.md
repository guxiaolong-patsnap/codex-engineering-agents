---
name: board-report
description: Emit a single SDLC board event payload outline for local NDJSON or ingest URL.
---

# board-report

Draft a board event with: `schema_version=1`, `run_id`, `timestamp`, `repo`, `agent`, `skill`, `step`, `status`.

Never include tokens or secrets. Prefer writing to `~/.eng-agent-team/runs/<run_id>.ndjson` when available.
