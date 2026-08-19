# Engineering Agents content catalog

This repository has two deliberately separate layers: the authored Engineering Agents catalog and the self-contained `eng-agents` Codex plugin. Neither is a generated runtime project.

## Scope

Allowed content:

- project-discoverable sub-agent definitions in `.codex/agents/*.toml`;
- repository-discoverable skills in `.agents/skills/<id>/SKILL.md` and necessary skill resources;
- the distributable plugin under `plugins/eng-agents/`;
- secret-free logical CLI/MCP integration declarations under `integrations/`;
- catalog metadata, canonical schema, deterministic validator, tests, and contributor documentation.

Do not add runtime `config.toml`, bound-repository files, local paths, credentials, automation specifications, schedule IDs, run logs, locks, claims, cursors, or generated runtime artifacts. They belong only in the generated Mac mini runtime project. Plugin lifecycle code belongs under `plugins/eng-agents/` and must remain self-contained.

## Authoring invariants

- Preserve `.codex/agents` and `.agents/skills` discovery paths.
- Every authored agent, skill, and integration must be declared exactly once in `catalog/manifest.json`.
- IDs, filenames/directories, TOML `name`, and skill frontmatter `name` must agree.
- Dependencies must be typed, resolvable, and acyclic.
- Agent TOMLs define role, instructions, and sandbox only. The runtime control plane chooses model and reasoning policy.
- Integration declarations name logical capabilities and runtime-managed authentication modes; never store secret values.
- Dispatcher skills may coordinate declared agents/skills. Avoid recursive dispatch cycles.
- `scheduled-issue-poll` owns issue polling behavior and invokes `$issue-pipeline`; setup and scheduling stay in the plugin.
- Do not merge or publish without explicit human intent.

## Required validation

Run before handoff:

```bash
python3 scripts/validate_catalog.py
python3 -m unittest discover -s tests -v
```

For each new or changed skill, also run the `skill-creator` `quick_validate.py` against its directory. Report validation evidence and any compatibility risk.
