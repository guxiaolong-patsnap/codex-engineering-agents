---
name: eng-agents-run-now
description: Run the selected catalog entrypoint immediately for an existing Engineering Agents runtime without mutating private Scheduled Task state.
---
# eng-agents-run-now

Run `python3 "${PLUGIN_ROOT}/scripts/setup.py" run-now --project <runtime>`. Execute the returned thin prompt with all returned project paths in the current Codex conversation. Do not invent another agent or skill name and do not write private automation state.
