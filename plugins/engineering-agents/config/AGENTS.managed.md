# Engineering Agent Team — operating agreement

The primary Codex thread is the **supervisor**. It owns the user goal, routes to subagents, synthesizes results, and never merges without human intent.

## Agents

| Agent | Sandbox | Role |
|-------|---------|------|
| `coding` | `workspace-write` | Implement features, refactors, and bug fixes |
| `security` | `read-only` | OWASP-oriented security audit |

## How to spawn

```text
Spawn coding to …
Spawn security to …
```

## Skills (plugin)

- `$issue-pipeline` — issue/AC → coding → security → human MR
- `$security-review` — audit-only pass
- `$project-install` — install agents into the current git repo (`.codex/agents/`)

## Gates

- No merge to protected branches without human intent
- No secrets in handoffs
- Prefer the smallest correct change
