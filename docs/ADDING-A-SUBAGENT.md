# Adding a project-scoped subagent

**Put the agent under `.codex/agents/`** (not `~/.codex/agents/` for shared product roles).

1. Create `.codex/agents/<name>.toml`:

```toml
name = "<name>"
description = "When the supervisor should spawn this role."
sandbox_mode = "read-only" # or workspace-write

developer_instructions = """
Role instructions...
End with a ## Handoff block.
"""
```

2. Register in `.codex/config.toml`:

```toml
[agents.<name>]
description = "Same idea as the TOML description."
config_file = "agents/<name>.toml"
```

3. Keep multi-agent enabled:

```toml
[features]
multi_agent_v2 = true

[agents]
enabled = true
```

4. Open this repository in Codex and **trust the project**.

Docs: https://developers.openai.com/codex/subagents
