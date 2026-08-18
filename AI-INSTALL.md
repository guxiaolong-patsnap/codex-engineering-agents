# AI agent install guide — engineering-agents

## 方式 1：PatSnap 插件市场（推荐）

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add engineering-agents@openai-plugins
```

同步 subagents 到 `~/.codex/agents/`（装插件后执行一次）：

```bash
git clone --depth 1 https://github.com/guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents
bash /tmp/eng-agents/plugins/engineering-agents/scripts/install.sh
```

启用 multi-agent（若尚未配置）：

```toml
[features]
multi_agent_v2 = true

[agents]
enabled = true
```

会话技能：`$issue-pipeline`、`$security-review`、`$project-install`。

## 方式 2：项目级 install（团队 via git）

```bash
git clone --depth 1 https://github.com/guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents
bash /tmp/eng-agents/install.sh --into /path/to/business-repo
```

写入 `<project>/.codex/agents/`、`.codex/config.toml`、`.codex/.engineering-agents-manifest.json`、`AGENTS.md` 管理块。  
**不**修改 `~/.codex/agents/`。

## 升级

- Plugin：`codex plugin marketplace upgrade openai-plugins` + `scripts/install.sh`
- 项目级：重跑 `install.sh --into <project>`
