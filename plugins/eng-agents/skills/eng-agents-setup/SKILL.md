---
name: eng-agents-setup
description: Initialize a generated Engineering Agents Codex runtime project on a Mac, bind repositories, and return versioned Scheduled Task desired state.
---

# eng-agents-setup

This plugin is the setup/control plane. It shares a repository with the `codex-engineering-agents` content catalog, but never run either the catalog checkout or installed plugin cache as the production execution project.

Prerequisite: install catalog-declared provider skills through the approved company distribution channel. The initial catalog requires `company-gitlab-api-query`; setup must fail closed if provider resolution or its declared health check fails.

## One command (preferred)

```bash
python3 "${PLUGIN_ROOT}/scripts/setup.py" --into ~/Codex/engineering-agents/projects/issue-worker-prod --ref v1.0.0
```

This will:

1. Resolve the catalog ref to a commit and validate `catalog/manifest.json`
2. Materialize declared agents and skills into a generated runtime project
3. Open the browser UI for repository, routing, entrypoint, and interval choices
4. Return a versioned `ScheduleIntent`

Ask the user to open and Trust the generated runtime project, not the catalog checkout.

After setup completes, use the returned `ScheduleIntent` exactly. It contains the catalog-selected entrypoint skill, thin prompt, recurrence, runtime instance path, and every project path. Do not substitute names from plugin code.

The one-command flow runs deep readiness checks before returning the intent. Do not create the Scheduled Task unless catalog/runtime digests, business checkout remote/write probes, provider skill resolution, and declared integration health checks all pass.

Use Codex's Scheduled Task/automation capability to create or update this task. Do not write or edit `automation.toml`, `.codex/automations/eng-agents.json`, or any other raw automation state file. Confirm the task in the Codex App's **Scheduled** view.

Optional:

- `--ref <protected-tag-or-sha>` (defaults to `v1.0.0`; never schedule mutable `main`)
- `--expected-digest sha256:<hex>` or `ENG_AGENTS_CATALOG_DIGEST` when deployment policy pins a trusted release digest
- `ENG_AGENTS_CATALOG_URL` to override the catalog source
- `--skip-clone` to reuse the pinned catalog recorded in the runtime lock

## Single steps (rare)

```bash
python3 "${PLUGIN_ROOT}/scripts/setup.py" materialize --into ~/Codex/engineering-agents/projects/issue-worker-prod
python3 "${PLUGIN_ROOT}/scripts/setup.py" ui --project ~/Codex/engineering-agents/projects/issue-worker-prod --skip-clone
python3 "${PLUGIN_ROOT}/scripts/setup.py" schedule --project ~/Codex/engineering-agents/projects/issue-worker-prod
```

After setup: confirm the generated runtime is trusted and Codex App → Scheduled matches the returned intent.

Use `$eng-agents-update`, `$eng-agents-doctor`, `$eng-agents-schedule`, and `$eng-agents-run-now` for ongoing lifecycle operations.
