---
name: onboard-repos
description: Ensure repos are bound for Engineering Agent Team work; open onboard guidance if binding is missing.
---

# onboard-repos

## Steps

1. Check for `~/.eng-agent-team/projects.json` (or `$ENG_AGENT_TEAM_HOME/projects.json`).
2. If missing, tell the user how to create it (provider, repo id, enabled flag) and wait.
3. Summarize enabled projects.
4. Suggest next skill: `$feature-pipeline` or `$bugfix-lite`.

## Constraints

- Do not invent repositories
- Do not push or merge
