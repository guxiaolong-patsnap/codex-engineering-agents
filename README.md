# codex-engineering-agents

PatSnap Codex 插件 **eng-agents** 产品仓。市场在 [openai-plugins](http://git.patsnap.com/patsnap/openai-plugins)，本仓只放插件源码。

## 安装

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add eng-agents@patsnap-openai-plugins
```

## 使用

在 Codex 中 Trust 执行项目后：

```text
Run $eng-agents-setup
```

或：

```bash
bash plugins/eng-agents/scripts/open-setup-ui.sh --project .
```

会写入 `.git_projects.json`、`.codex/agents/`、`.codex/automations/eng-agents.json`。

| Skill | 作用 |
|-------|------|
| `$eng-agents-setup` | 绑定仓库、物化 agents、配置 automation |
| `$issue-pipeline` | Issue → coding → security |
| `$security-review` | 安全审计 |

## 发布

改代码 → bump `plugins/eng-agents/.codex-plugin/plugin.json` version → push `main` → `codex plugin marketplace upgrade patsnap-openai-plugins`。
