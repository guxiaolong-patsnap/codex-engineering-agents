# Architecture

**Project-scoped agents live in `.codex/agents/`**, following
[proflead/codex-agents-library](https://github.com/proflead/codex-agents-library).

```text
.codex/
  config.toml          # multi_agent_v2, max_threads, max_depth
  agents/
    coding.toml
    security.toml
```

| Agent | Sandbox | Purpose |
|-------|---------|---------|
| `coding` | workspace-write | Implement / fix / draft-ready diffs |
| `security` | read-only | OWASP-oriented audit |

Clone → open as Codex project root → trust → `Spawn coding|security to …`.

Plugins under `plugins/` are optional for skills; they are not the home for role TOMLs.
