---
name: eng-agents-rollback
description: Atomically switch a generated Engineering Agents runtime back to a retained, digest-verified catalog generation while preserving bindings and state.
---

# eng-agents-rollback

Run `python3 "${PLUGIN_ROOT}/scripts/setup.py" rollback --project <runtime>`. By default this activates the most recently retained generation other than the current one. Use `--generation <exact-id>` only for a generation listed under `.eng-agents/generations/`.

Then run `$eng-agents-doctor` and reconcile the Scheduled Task if its prompt or entrypoint changed. Never delete business checkouts, bindings, secrets, logs, or claim history during rollback.
