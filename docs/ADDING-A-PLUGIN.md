# Adding a Codex plugin

Follow the official plugin layout:

```text
plugins/<name>/
  .codex-plugin/plugin.json   # only the manifest here
  skills/<skill>/SKILL.md
  hooks/                      # optional
  .mcp.json                   # optional
  assets/                     # optional
```

Register it in `.agents/plugins/marketplace.json`:

```json
{
  "name": "<name>",
  "source": { "source": "local", "path": "./plugins/<name>" },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Development"
}
```

Then:

```bash
codex plugin marketplace upgrade codex-engineering-agents
codex plugin add <name>@codex-engineering-agents
```

Docs: https://developers.openai.com/codex/plugins/build
