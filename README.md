# codex-engineering-agents

PatSnap Codex 插件 **eng-agents**。市场：[openai-plugins](http://git.patsnap.com/patsnap/openai-plugins)。

## 目录

```text
.
├── .codex/
│   ├── agents/          # subagent 定义（唯一源）
│   └── config.toml
├── .codex-plugin/       # 插件 manifest
├── AGENTS.md
├── skills/              # $eng-agents-setup / $issue-pipeline / …
├── ui/setup/            # 配置页
├── scripts/             # setup / apply
├── schemas/
├── config/              # managed-manifest
└── assets/
```

## 安装

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add eng-agents@patsnap-openai-plugins
```

本仓可直接作为 Codex 执行项目（Trust 后加载 `.codex/agents/`）。

## 使用

```text
Run $eng-agents-setup
```

或：

```bash
bash scripts/open-setup-ui.sh --project .
```

| Skill | 作用 |
|-------|------|
| `$eng-agents-setup` | 绑定仓库、配置 automation |
| `$issue-pipeline` | Issue → coding → security |
| `$security-review` | 安全审计 |

新增/修改 subagent：编辑 `.codex/agents/*.toml`。

## 发布

bump `.codex-plugin/plugin.json` version → push `main` → `codex plugin marketplace upgrade patsnap-openai-plugins`。
