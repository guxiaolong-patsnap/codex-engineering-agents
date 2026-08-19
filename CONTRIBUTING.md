# Contributing

This repository publishes versioned Engineering Agents content and contains its `eng-agents` plugin consumer at `plugins/eng-agents/`. Keep generated runtime behavior out of both source layers.

## Add or change an agent

1. Add or edit `agents/<id>.toml`.
2. Keep `name` equal to `<id>` and use a stable lowercase kebab-case ID.
3. Define a focused role, handoff contract, and least-privilege `sandbox_mode`.
4. Do not set `model` or `model_reasoning_effort`; runtime instance policy owns both.
5. Declare the agent, owner, and logical dependencies in `catalog/manifest.json`.

## Add or change a skill

1. Use `agents/skills/<id>/SKILL.md` and the same `name` in YAML frontmatter.
2. Keep discovery text concise and workflow instructions free of machine-specific setup.
3. Declare its owner, `dispatcher` or `specialist` kind, and typed dependencies in the manifest.
4. A dispatcher may invoke only declared agents or skills. Do not create dependency cycles.
5. Run the `skill-creator` quick validator for every changed skill.

## Add a logical integration

Place a declaration at `integrations/<kind>/<id>/integration.json`, where `<kind>` is `cli` or `mcp`. Describe:

- the approved provider or adapter;
- logical capabilities consumed by skills;
- read/write access level;
- runtime-managed authentication mode;
- a non-mutating health check when available.

Do not include tokens, passwords, private keys, token-cache contents, machine-specific paths, or production credentials. Installation, connection, endpoint selection, SSO, and health-check execution belong to `plugins/eng-agents/`.

## Change the contract

`catalog/manifest.schema.json` is the canonical authoring schema. Contract changes require:

1. a deliberate `apiVersion` or compatible schema evolution decision;
2. matching validator and unittest changes;
3. matching changes to the plugin consumer in `plugins/eng-agents/` before publishing;
4. an updated `catalogVersion` and compatibility range.

The plugin may cache the schema for offline use only when it records the source release and digest; do not manually maintain a second canonical schema.

## Validate a change

```bash
python3 scripts/validate_catalog.py
python3 -m unittest discover -s tests -v
```

The validator uses only the Python standard library and checks JSON/TOML parsing, skill frontmatter, discovery paths, names, dependencies, dangling references, cycles, and basic embedded-secret patterns.

Open a merge request with the changed catalog version, compatibility impact, test evidence, owners, and rollout risk. Publishing or merging still requires explicit human intent.
