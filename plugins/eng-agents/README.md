# eng-agents（插件）

Mac mini 上 Engineering Agents 的唯一设置与生命周期控制面。插件与内容 catalog 均位于 `guxiaolong-patsnap/codex-engineering-agents`；公司 marketplace 只保留该仓的 `git-subdir` 入口。

| 职责 | 位置 |
|------|------|
| 本插件 | catalog 获取/校验、生成 Runtime、绑定、doctor/update/rollback、Scheduled Task 期望状态 |
| 同仓内容目录 | 根目录的 agent TOML、skill、integration 声明、`catalog/manifest.json` |
| Runtime | 插件在 Mac 上生成并由 Codex 打开/Trust 的执行项目 |

## 安装

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add eng-agents@patsnap-openai-plugins
```

## 使用

```text
Run $eng-agents-setup
```

或一条命令：

```bash
python3 scripts/setup.py --into ~/Codex/engineering-agents/projects/issue-worker-prod --ref v1.0.0
```

内容仓 checkout/cache 不是 Runtime。默认从正式 `patsnap/codex-engineering-agents` 仓解析受保护的 `v1.0.0` tag；流程是 tag/SHA 解析到 commit → manifest/依赖与可选 `--expected-digest` 校验 → 物化运行项目 → 浏览器绑定 → 返回版本化 `ScheduleIntent` → 由 Codex 对话创建或更新 Scheduled Task。

前置条件：catalog 声明的 provider skill/CLI 必须先由公司批准的分发渠道安装。当前 `company-gitlab` 需要 `company-gitlab-api-query` skill。setup 和 `schedule` 会解析其脚本路径并执行声明的 `capabilities` 健康检查；缺失、未登录或不可达时阻止创建 Scheduled Task，不会生成一个注定失败的任务。

Git catalog 必须与解析出的 commit 完全一致且工作树干净，声明的载荷必须全部被该 commit 跟踪。catalog URL 禁止内嵌 userinfo/token、query 或 fragment，认证应走 SSH 或 Git credential helper。本地非 Git 目录仅可在开发验证时显式加 `--allow-filesystem-catalog` 做 `materialize`；控制面会拒绝由它创建或立即运行 Scheduled Task。

单步：

```bash
python3 scripts/setup.py doctor --project ~/Codex/engineering-agents/projects/issue-worker-prod
python3 scripts/setup.py update --project ~/Codex/engineering-agents/projects/issue-worker-prod --ref v1.1.0
python3 scripts/setup.py rollback --project ~/Codex/engineering-agents/projects/issue-worker-prod
python3 scripts/setup.py schedule --project ~/Codex/engineering-agents/projects/issue-worker-prod
python3 scripts/setup.py run-now --project ~/Codex/engineering-agents/projects/issue-worker-prod
```

`ui` 始终读取 Runtime 当前 `current` generation 的 catalog 选项；它不会因为默认 ref 或命令行 ref 不同而偷偷切换内容。要改变 catalog 版本，先显式运行 `update --ref <tag-or-sha>`，通过 doctor 后再打开 UI。

## 目录

```text
plugins/eng-agents/
├── .codex-plugin/plugin.json
├── skills/eng-agents-setup/
├── scripts/setup.py          # 兼容入口
├── scripts/eng_agents.py     # 控制面实现
├── ui/setup/
├── contracts/v1/
└── assets/
```

每次更新先写入 `.eng-agents/generations/<commit>-<digest>/` 并校验，再通过 `current` 链接切换；上一代保留用于回滚。定时 prompt 使用生成的 `.eng-agents/runtime_state.py` 取得单实例 lease 和带 TTL 的 issue claim，避免相邻轮询重复处理同一问题。
