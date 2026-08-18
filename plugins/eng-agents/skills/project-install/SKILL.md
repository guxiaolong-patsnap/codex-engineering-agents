---
name: project-install
description: Install eng-agents into the current git repository at .codex/agents/ (project-scoped, team-shared via git). Does not modify ~/.codex/agents.
---

# project-install

## When to use

- First time using eng-agents in a business git repo
- Team wants agents vendored into the repo (not personal `~/.codex/`)
- Upgrade after plugin version bump

## Steps

1. Confirm the workspace root is a git repository (or user accepts `--force`).
2. Run the plugin install script:

```bash
bash "${PLUGIN_ROOT:-./plugins/eng-agents}/scripts/install-project.sh" --into .
```

3. Tell the user to trust the project, then commit `.codex/` and `AGENTS.md`.

## What gets written

| Path | Purpose |
|------|---------|
| `.codex/agents/coding.toml` | Coding subagent |
| `.codex/agents/security.toml` | Security subagent |
| `.codex/config.toml` | Enables multi-agent |
| `AGENTS.md` | Managed block |
| `.codex/.eng-agents-manifest.json` | Reinstall manifest |
