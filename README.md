# codex-engineering-agents

Codex engineering multi-agent team. **Project-scoped subagents live in `.codex/agents/`** (official Codex layout).

## Layout

```text
.codex/
  config.toml              # multi_agent + role registry
  agents/*.toml            # ★ project-scoped subagents (design/coding/eval/sre)
.agents/plugins/marketplace.json
plugins/eng-agent-team/    # installable skills (plugin)
AGENTS.md                  # primary-thread / supervisor contract
```

Official refs: [Subagents](https://developers.openai.com/codex/subagents) · [Plugins](https://developers.openai.com/codex/plugins/build)

## Personal machine

```bash
git clone https://github.com/guxiaolong-patsnap/codex-engineering-agents.git
cd codex-engineering-agents
# Open this folder in Codex and trust the project
```

Subagents load from `.codex/agents/`. Optional skills:

```bash
./scripts/register-marketplace.sh
codex plugin add eng-agent-team@codex-engineering-agents
```

## Mac Mini (shared)

1. Clone (or pull tags) to a fixed path, e.g. `/opt/codex-engineering-agents`
2. Trust the project once in Codex
3. Run agent sessions with this repo as the project root (or attached workspace)
4. Upgrade: `git fetch --tags && git checkout vX.Y.Z`

Do **not** rely on copying agents into `~/.codex/agents` as the product path.

## Add a subagent

See [docs/ADDING-A-SUBAGENT.md](docs/ADDING-A-SUBAGENT.md) — files go under `.codex/agents/`.

## Design

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
