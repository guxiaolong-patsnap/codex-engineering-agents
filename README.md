# codex-engineering-agents

**Engineering Agents** 产品仓：Codex subagents（`coding` + `security`）、skills、项目级 install。  
**分发入口**：PatSnap 插件市场 [`openai-plugins`](http://git.patsnap.com/patsnap/openai-plugins)（Git 指针，代码仍在本仓）。

## 推荐：PatSnap 插件市场安装

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add engineering-agents@openai-plugins
```

安装后同步 subagents 到 `~/.codex/agents/`：

```bash
# 从插件缓存或本仓 clone 运行
bash plugins/engineering-agents/scripts/install.sh
```

Desktop：重启 ChatGPT / Codex App → Plugins Directory → **PatSnap Engineering Agents** → 安装 **Engineering Agents**。

### 插件技能

| Skill | 用途 |
|-------|------|
| `$issue-pipeline` | Issue/AC → coding → security → 人工 MR |
| `$security-review` | 只读安全审计 |
| `$project-install` | 把 agents 装进当前 git 仓 `.codex/` |

## 备选：项目级安装（团队 via git）

不依赖个人 `~/.codex/`，agents 跟业务仓走：

```bash
git clone --depth 1 https://github.com/guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents
bash /tmp/eng-agents/install.sh --into /path/to/your-app
cd /path/to/your-app && codex
```

装好后提交 `.codex/` + `AGENTS.md`。

## 备选：控制面模式

```bash
./setup --repo /path/to/your-app
./eng issue "Implement …"
```

## 目录

```text
plugins/engineering-agents/          # 插件根（市场 git-subdir 指向此处）
  .codex-plugin/plugin.json
  agents/                            # 源：coding + security
  skills/
  scripts/
install.sh                           # → install-project.sh
setup / eng                          # 控制面（可选）
```

Agent 源：`plugins/engineering-agents/agents/`。本仓开发跑 `./scripts/sync-local-dev.sh`。

## Agents

| Agent | Sandbox | Role |
|-------|---------|------|
| `coding` | `workspace-write` | 实现 / 修复 |
| `security` | `read-only` | 安全审计 |

详见 [docs/PLUGIN.md](docs/PLUGIN.md)、[AI-INSTALL.md](AI-INSTALL.md)。
