# codex-engineering-agents

**eng-agents** 产品仓：Codex subagents（`coding` + `security`）、skills、项目级 install。  
**分发**：PatSnap 市场 [`openai-plugins`](http://git.patsnap.com/patsnap/openai-plugins)（git-subdir 指针）。

## 安装（PatSnap 市场）

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add eng-agents@patsnap-openai-plugins
```

同步 subagents：

```bash
git clone --depth 1 https://github.com/guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents
bash /tmp/eng-agents/plugins/eng-agents/scripts/install.sh
```

技能：`$issue-pipeline`、`$security-review`、`$project-install`。

## 项目级 install

```bash
bash install.sh --into /path/to/your-app
```

## 目录

```text
plugins/eng-agents/     # 插件根（市场 git-subdir 指向此处）
install.sh / setup / eng
```

Agent 源：`plugins/eng-agents/agents/`。
