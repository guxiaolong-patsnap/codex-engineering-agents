# codex-engineering-agents

[eng-agents](http://git.patsnap.com/patsnap/openai-plugins) 的产品仓。PatSnap 市场通过 **git-subdir** 指向 `plugins/eng-agents/`，本仓不含 marketplace 清单。

## 安装

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add eng-agents@patsnap-openai-plugins
bash plugins/eng-agents/scripts/install.sh   # 同步到 ~/.codex/agents
```

## 技能

| Skill | 说明 |
|-------|------|
| `$issue-pipeline` | Issue → coding → security |
| `$security-review` | 安全审计 |
| `$project-install` | 写入业务仓 `.codex/agents/` |

## 项目级安装

```bash
bash plugins/eng-agents/scripts/install-project.sh --into /path/to/repo
```

## 结构

```text
plugins/eng-agents/
  .codex-plugin/plugin.json
  agents/          coding.toml, security.toml
  skills/
  config/
  scripts/         install.sh, sync-agents.sh, install-project.sh
```

## 开发

改 `agents/` 或 `skills/` → bump `plugin.json` version → push `main` → 用户 `codex plugin marketplace upgrade patsnap-openai-plugins`。
