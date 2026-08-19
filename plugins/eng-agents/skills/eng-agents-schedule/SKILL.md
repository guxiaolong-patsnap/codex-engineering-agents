---
name: eng-agents-schedule
description: Produce versioned Scheduled Task desired state for a generated Engineering Agents runtime and reconcile it through supported Codex automation capabilities.
---
# eng-agents-schedule

Run `python3 "${PLUGIN_ROOT}/scripts/setup.py" schedule --project <runtime>`. Use the returned name, prompt, recurrence, enabled state, and every project path to create or update the task through the supported Codex conversation automation capability. Never write private automation files or database state. Read the created task back when the capability supports it.
