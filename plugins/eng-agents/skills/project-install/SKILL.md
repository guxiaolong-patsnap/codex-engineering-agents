---
name: project-install
description: Install eng-agents into the current git repo at .codex/agents/ (team-shared). Does not modify ~/.codex/agents.
---

# project-install

Run (from plugin root or clone):

```bash
bash "${PLUGIN_ROOT}/scripts/install-project.sh" --into .
```

Writes `.codex/agents/`, merges `.codex/config.toml`, upserts `AGENTS.md`, writes `.codex/.eng-agents-manifest.json`. Commit results for teammates.
