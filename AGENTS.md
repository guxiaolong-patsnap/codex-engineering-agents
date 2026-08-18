# Project operating agreement

This repository is the **control plane** for multi-agent work on one or more bound business git repos (see `./setup` / `./eng`).

## Supervisor

The primary Codex thread is the supervisor. It owns the user goal, chooses target repos, routes to subagents, synthesizes results, and never merges without human intent.

## Agents

- `coding` (`workspace-write`): implement features/fixes in bound repos
- `security` (`read-only`): OWASP-oriented audit of the change

## Drivers

- **Issue**: user or `./eng issue "…"` supplies issue/AC → spawn coding → spawn security → hand back for human MR/merge
- **Schedule**: `./eng schedule` / cron → pick at most one small task or report idle → same spawn chain

## How to spawn

```text
Spawn coding to …
Spawn security to …
```

## Gates

- No merge to protected branches without human intent
- No secrets in handoffs
- Prefer the smallest correct change
- Work only in bound business repos unless the user names another path
