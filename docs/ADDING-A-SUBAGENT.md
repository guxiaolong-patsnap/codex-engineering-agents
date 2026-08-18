# Adding a project-scoped subagent

Follow the [codex-agents-library](https://github.com/proflead/codex-agents-library) pattern.

1. Add `.codex/agents/<name>.toml` where `<name>` is `lowercase_underscore` and matches the `name` field.
2. Required fields: `name`, `description`, `developer_instructions`.
3. Recommended: `model`, `model_reasoning_effort`, `sandbox_mode`, `nickname_candidates`.
4. Open this repo in Codex and **trust the project**.

Example spawn: `Spawn <name> to …`

See existing `coding.toml` and `security.toml`.
