# AI agent install guide — project-scoped eng-agents

You are installing **codex-engineering-agents** into a **business git repository**
as project-scoped Codex subagents (`.codex/agents/`), NOT into `~/.codex/`.

This mirrors the one-command UX of [my-codex](https://github.com/sehoon787/my-codex),
but the install target is **per-repo** so the team shares agents via git.

## Fast path

From a checkout of this agents repo:

```bash
bash install.sh --into /absolute/path/to/business-repo
```

Or:

```bash
git clone --depth 1 https://github.com/guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents
bash /tmp/eng-agents/install.sh --into /path/to/business-repo
rm -rf /tmp/eng-agents
```

## What gets written (project only)

| Path | Contents |
|------|----------|
| `<project>/.codex/agents/coding.toml` | Coding agent |
| `<project>/.codex/agents/security.toml` | Security agent |
| `<project>/.codex/config.toml` | `multi_agent_v2` + agents enabled |
| `<project>/AGENTS.md` | Managed operating agreement block |
| `<project>/.codex/.eng-agents-manifest.json` | Manifest for safe reinstall |

Does **not** modify `~/.codex/agents/`.

## After install

```bash
cd /path/to/business-repo
codex
# Trust this project
# Spawn coding to …
# Spawn security to …
```

Commit the installed `.codex/` + `AGENTS.md` so teammates get the same agents on clone.

## Upgrade

Re-run the same `install.sh --into <project>`. Only paths listed in the previous
manifest are removed before rewrite; user-added agent TOMLs outside the manifest
are left alone.
