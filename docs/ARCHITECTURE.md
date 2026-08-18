# Architecture — Project-scoped subagents

**Decision (2026-08-18): use `.codex/agents/` for project-scoped agents.**

This matches Codex’s official layout ([Subagents](https://developers.openai.com/codex/subagents)):

| Scope | Path | Use |
|-------|------|-----|
| **Project (this product)** | `.codex/agents/*.toml` | Shared via git; clone + trust → available |
| Personal (optional, out of band) | `~/.codex/agents/*.toml` | Individual experiments; not what we distribute |

Plugins remain for **skills / marketplace** distribution. They are not the home for role definitions.

## 1. Why `.codex/agents/`

1. Official Codex discovery path for project agents  
2. Same experience for **personal clone** and **Mac Mini fixed checkout** (both trust this repo)  
3. Versioned with git tags; no silent drift in `~/.codex`  
4. Multi-agent registration stays next to the files in `.codex/config.toml`

## 2. Repository layout

```text
codex-engineering-agents/
├── AGENTS.md                      # supervisor / primary-thread contract
├── .codex/
│   ├── config.toml                # multi_agent + [agents.<role>] → config_file
│   └── agents/                    # ★ iterate here
│       ├── design.toml
│       ├── coding.toml
│       ├── eval.toml
│       └── sre.toml
├── .agents/
│   ├── plugins/marketplace.json   # Codex plugin catalog
│   └── skills/                    # optional repo skills (no install)
├── plugins/eng-agent-team/        # installable skills bundle
│   ├── .codex-plugin/plugin.json
│   └── skills/*/SKILL.md
├── docs/
└── scripts/register-marketplace.sh
```

## 3. How roles are wired

`.codex/config.toml` declares each role; `config_file` is relative to that config:

```toml
[features]
multi_agent_v2 = true

[agents]
enabled = true

[agents.coding]
description = "…"
config_file = "agents/coding.toml"   # → .codex/agents/coding.toml
```

Codex loads these when the **project is trusted** and the session is rooted in this repository.

## 4. Distribution model

| Consumer | How to run |
|----------|------------|
| Personal | `git clone` → open in Codex → **trust project** → spawn `design` / `coding` / … |
| Mac Mini | Fixed clone of this repo (pin tag) → trust once → run work **from this checkout** or attach this project; upgrade = `git fetch && git checkout vX.Y.Z` |
| Skills | `codex plugin marketplace add <repo>` + `codex plugin add eng-agent-team@…` |

**Do not** make `~/.codex/agents` the primary fleet install path for this product. That bypasses project trust and git versioning. Personal `~/.codex/agents` stays for local-only experiments.

If Mini must operate inside arbitrary business repos: keep a **trusted checkout of this agents repo** as the Codex project / workspace root for agent sessions (or multi-root), rather than copying TOMLs into every business repo.

## 5. Iteration rules

1. New / changed role → edit `.codex/agents/<name>.toml` + register in `.codex/config.toml`  
2. New workflow skill → `plugins/eng-agent-team/skills/<skill>/` (and marketplace if needed)  
3. Routing / gates → `AGENTS.md`  
4. One PR ≈ one agent TOML (or one skill), when possible  

## 6. Later (optional)

If agent folders grow (many skills / references per role), introduce `agents/<id>/` as an **authoring** tree that **generates** `.codex/agents/<id>.toml`. Until then, **`.codex/agents/` is the source of truth**.
