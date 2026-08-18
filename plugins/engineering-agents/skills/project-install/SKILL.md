---
name: project-install
description: Install engineering-agents into the current git repository at .codex/agents/ (project-scoped, team-shared via git). Does not modify ~/.codex/agents.
---

# project-install

## When to use

- First time using engineering-agents in a business git repo
- Team wants agents vendored into the repo (not personal `~/.codex/`)
- Upgrade after plugin version bump

## Steps

1. Confirm the workspace root is a git repository (or user accepts `--force`).
2. Run the plugin install script:

```bash
bash "${PLUGIN_ROOT:-./plugins/engineering-agents}/scripts/install-project.sh" --into .
```

If `PLUGIN_ROOT` is set (plugin context), use that path. Otherwise resolve from a clone of the product repo.

3. Tell the user to:
   - `codex` in the project root
   - Trust the project when prompted
   - Commit `.codex/` and the managed `AGENTS.md` block for teammates

## What gets written

| Path | Purpose |
|------|---------|
| `.codex/agents/coding.toml` | Coding subagent |
| `.codex/agents/security.toml` | Security subagent |
| `.codex/config.toml` | Enables `multi_agent_v2` + agents |
| `AGENTS.md` | Managed operating agreement block |
| `.codex/.engineering-agents-manifest.json` | Safe reinstall manifest |

## Constraints

- Does **not** write to `~/.codex/agents/`
- Only replaces files listed in the previous manifest on upgrade
- User-added custom agent TOMLs outside the manifest are preserved

## After install

Use `$issue-pipeline` or spawn agents directly:

```text
Spawn coding to …
Spawn security to …
```
