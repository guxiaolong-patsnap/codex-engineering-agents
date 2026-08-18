# Project operating agreement

This repository ships Codex **plugins** (under `plugins/`) and **project subagents** (under `.codex/agents/`).

## Supervisor

The primary Codex thread is the supervisor. It owns the user goal, routing, synthesis, and final answer. Subagents return structured handoffs; they do not pass work directly to one another.

## Project subagents

Registered in `.codex/config.toml`:

- `design` — requirements / intake / acceptance criteria
- `coding` — implement changes toward a draft MR
- `eval` — independent quality / security / acceptance checks
- `sre` — release / observe (explicit request only; no silent prod changes)

## Plugins

Installable skills live in the local marketplace (`.agents/plugins/marketplace.json`). Prefer invoking skills with `$skill-name` for repeatable workflows.

## Gates

- No merge to protected branches without human intent
- No secrets in board events or handoffs
- Prefer the smallest correct change
