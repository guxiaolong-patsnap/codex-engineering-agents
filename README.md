# codex-engineering-agents

PatSnap Engineering Agents 单一源码仓。各工程团队在这里维护可分发的 sub-agent TOML、skills、逻辑 CLI/MCP 集成声明，以及对应的 `eng-agents` 插件控制面。

本仓不保存任何生成态 runtime。`plugins/eng-agents` 负责安装、Mac mini 初始化、业务仓绑定、凭证引用、模型策略和定时任务设置；它读取同仓的版本化 catalog，将固定版本物化到受信任的 Codex runtime project。

## 架构边界

```text
codex-engineering-agents
├── 内容作者源：agent / skill / integration / catalog
├── plugins/eng-agents：安装、绑定、校验、调度
└── Mac mini runtime project：生成态 agent / skill / 配置 / 状态
```

- **本仓拥有**：`.codex/agents/*.toml`、`.agents/skills/*/SKILL.md`、逻辑集成声明、catalog manifest/schema、内容校验与测试。
- **插件拥有**：`plugins/eng-agents` 中的内容获取与固定版本、runtime project 生成、业务仓绑定、MCP/CLI 安装和健康检查、Scheduled Task reconcile、升级与回滚。
- **runtime project 拥有**：实例配置、凭证引用、锁、claim、cursor、日志和真实 Scheduled Task ID。生成态文件不得回写本仓。

## 目录

```text
.
├── .codex/agents/                         # Codex sub-agent 发现路径（唯一作者源）
│   ├── coding.toml
│   └── security.toml
├── .agents/skills/                        # Codex repo skill 发现路径（唯一作者源）
│   ├── issue-pipeline/SKILL.md
│   ├── security-review/SKILL.md
│   └── scheduled-issue-poll/SKILL.md
├── catalog/
│   ├── manifest.json                      # 插件消费的 v1 内容清单
│   └── manifest.schema.json               # canonical manifest schema
├── integrations/cli/company-gitlab/
│   └── integration.json                   # 无凭证的逻辑能力声明
├── plugins/eng-agents/                    # git-subdir 安装单元；必须自包含
│   ├── .codex-plugin/plugin.json
│   ├── skills/                             # setup / doctor / update 等插件技能
│   ├── scripts/                            # 控制面实现
│   └── contracts/
├── scripts/validate_catalog.py            # 仅使用 Python 标准库
├── tests/test_validate_catalog.py
├── AGENTS.md
└── CONTRIBUTING.md
```

`.codex/agents` 与 `.agents/skills` 是 Codex 的发现路径，必须保留。catalog 中的 agent 路径必须指向 TOML 文件，skill 路径必须指向完整 skill 目录；这样 digest、密钥扫描和物化都会覆盖 `scripts/`、`references/`、`assets/` 等配套资源。

## Catalog 契约

`catalog/manifest.json` 使用 `eng-agents.patsnap.com/v1`，包含：

- `catalogVersion` 与插件版本兼容范围；
- agent、skill、integration 的稳定 ID、相对路径和 owner；
- skill 的 `dispatcher` / `specialist` 分类；
- 类型化依赖，供插件做完整性检查和确定性物化；
- 供 Scheduled Task 使用的逻辑入口点，例如 `scheduledIssuePoll`。

清单只引用逻辑集成。`company-gitlab` 声明批准的只读 Skill Gateway 客户端与能力，不保存 endpoint token、用户凭证或本机绝对路径。

## 本地校验

需要 Python 3.9 或更高版本；不需要第三方 Python 包：

```bash
python3 scripts/validate_catalog.py
python3 -m unittest discover -s tests -v
```

修改 skill 后还要使用 Codex `skill-creator` 提供的 `quick_validate.py` 检查对应 skill 目录。公司 marketplace 仅保留 `git-subdir` 入口，路径为 `./plugins/eng-agents`。贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。
