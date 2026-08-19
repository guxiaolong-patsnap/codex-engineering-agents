---
name: eng-agents-update
description: Resolve an Engineering Agents catalog ref to a commit and update a generated runtime while preserving bindings and runtime state.
---
# eng-agents-update

Run `python3 "${PLUGIN_ROOT}/scripts/setup.py" update --project <runtime> --ref <tag-or-sha>`. Prefer a protected release tag or explicit SHA. The controller stages and digest-verifies a new generation before atomically switching `current`, while preserving `.eng-agents/bindings.json`, state, logs, and the previous generation. Then run `$eng-agents-doctor`; use `$eng-agents-rollback` if acceptance checks fail.
