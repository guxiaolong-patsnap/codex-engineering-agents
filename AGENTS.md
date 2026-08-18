# Project operating agreement

This repository ships **project-scoped** Codex subagents in `.codex/agents/`.

## Supervisor

The primary Codex thread is the supervisor. It owns the user goal, routing, synthesis, and final answer. Subagents return structured handoffs; they do not chain to each other unless you explicitly ask for orchestration.

## Agents

- `coding` (`workspace-write`): implement features/fixes; no merge without human intent
- `security` (`read-only`): OWASP-oriented audit; severity-ordered findings

## How to spawn

```text
Spawn coding to …
Spawn security to …
```

## Gates

- No merge to protected branches without human intent
- No secrets in handoffs
- Prefer the smallest correct change
