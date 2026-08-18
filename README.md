# codex-engineering-agents

为业务 Git 项目提供 **项目级** Codex 多 agent（`coding` + `security`）。  
安装思路参考 [my-codex](https://github.com/sehoon787/my-codex) 的一键 `install.sh`，但目标是 **`<project>/.codex/`**，不是个人 `~/.codex/`。

## 推荐：装进业务仓（项目级）

```bash
# 拿到本仓（或直接用 raw 脚本 clone）
git clone --depth 1 git@github.com:guxiaolong-patsnap/codex-engineering-agents.git /tmp/eng-agents

# 一条命令装进业务项目
bash /tmp/eng-agents/install.sh --into /path/to/your-app

# 进入业务仓使用
cd /path/to/your-app
codex
# Trust this project
# Spawn coding to … / Spawn security to …
```

装好后把 `.codex/` 与 `AGENTS.md` **提交进业务仓**，同事 clone 即可共用同一套 agents。

| my-codex（个人级） | 本方案（项目级） |
|--------------------|------------------|
| 写入 `~/.codex/agents/` | 写入 `<repo>/.codex/agents/` |
| 本机全局生效 | 跟 git 走，团队一致 |
| `curl \| bash` 装到家目录 | `install.sh --into <repo>` |

升级：对同一路径再跑一次 `install.sh --into …`（只替换 manifest 里登记的文件）。

详见 [AI-INSTALL.md](AI-INSTALL.md)。

## 备选：控制面模式（本仓启动，--add-dir 挂业务仓）

适合一台 Mac Mini 盯多个仓、又不想改业务仓内容时：

```bash
git clone git@github.com:guxiaolong-patsnap/codex-engineering-agents.git
cd codex-engineering-agents
chmod +x setup eng install.sh
./setup --repo /path/to/your-app
./eng
```

## Layout（本仓源）

```text
.codex/agents/{coding,security}.toml
.codex/config.toml
AGENTS.md
install.sh          # → 业务仓 .codex/（项目级）
setup / eng         # 控制面模式
```

## Agents

| Agent | Sandbox | Role |
|-------|---------|------|
| `coding` | `workspace-write` | 实现 / 修复 |
| `security` | `read-only` | 安全审计 |

合并默认人审；不自动 merge。
