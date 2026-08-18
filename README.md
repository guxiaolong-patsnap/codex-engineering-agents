# codex-engineering-agents

Project-scoped Codex subagents under `.codex/agents/`, following the layout of
[proflead/codex-agents-library](https://github.com/proflead/codex-agents-library).

## Layout

```text
.codex/
  config.toml           # multi_agent + max_threads / max_depth
  agents/
    coding.toml         # implementation
    security.toml       # security audit (read-only)
AGENTS.md
```

## Quick start

1. Clone this repo and open it as the Codex project root.
2. Trust the project so `.codex/` loads.
3. Spawn explicitly:

```text
Spawn coding to implement … with tests
Spawn security to audit this branch for OWASP and auth risks
```

Codex spawns subagents when asked (or when `AGENTS.md` / skills instruct). Config keeps `max_depth = 1` and `max_threads = 6`.

## Agents

| Agent | Sandbox | Role |
|-------|---------|------|
| `coding` | `workspace-write` | Features, fixes, draft-ready diffs |
| `security` | `read-only` | OWASP / auth / data-exposure review |

## Optional skills plugin

```bash
./scripts/register-marketplace.sh
codex plugin add eng-agent-team@codex-engineering-agents
```

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ADDING-A-SUBAGENT.md](docs/ADDING-A-SUBAGENT.md)
