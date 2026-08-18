# Engineering Agents

Primary thread is the **supervisor**: route work, spawn subagents, synthesize results. Do not merge without human intent.

Bound repos are listed in `.git_projects.json`; mount with `--add-dir`.

## Agents

| Agent | Sandbox | Role |
|-------|---------|------|
| `coding` | `workspace-write` | Implement features, refactors, fixes |
| `security` | `read-only` | Security audit |

```text
Spawn coding to …
Spawn security to …
```

## Skills

- `$eng-agents-setup` — bind repos, agents, automation
- `$issue-pipeline` — issue → coding → security
- `$security-review` — audit only

## Gates

- No merge to protected branches without human intent
- No secrets in handoffs or `.git_projects.json`
- Prefer the smallest correct change
