---
name: eng-agents-setup
description: Open setup UI to bind git repos, materialize .codex/agents/, and configure issue-poll automation for the current Codex project.
---

# eng-agents-setup

## Steps

1. Confirm cwd is the Codex execution project (Trust this project).
2. Open UI:

```bash
bash "${PLUGIN_ROOT}/scripts/open-setup-ui.sh" --project .
```

3. In the UI: add repos (with local `path`), routing rules, automation interval → **保存并应用**.
4. Confirm Codex App → Automations shows the issue-poll task.

Without UI:

```bash
# write .git_projects.json first, then:
bash "${PLUGIN_ROOT}/scripts/apply-setup.sh" --project .
```

Re-run anytime to edit bindings.
