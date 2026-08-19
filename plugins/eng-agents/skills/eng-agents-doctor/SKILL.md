---
name: eng-agents-doctor
description: Check a generated Engineering Agents runtime, its pinned catalog digest, materialized assets, bindings, project paths, and selected entrypoint.
---
# eng-agents-doctor

Run `python3 "${PLUGIN_ROOT}/scripts/setup.py" doctor --project <runtime>`. During first activation, credential refresh, or Mac mini readiness checks, add `--deep` to resolve provider skill paths and execute each declared integration health check; this may open an approved interactive login. Report every failed check. Do not repair or overwrite state unless the user separately requests update or setup.
