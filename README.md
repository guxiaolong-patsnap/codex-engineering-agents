# codex-engineering-agents

PatSnap **Engineering Agents** 产品仓：项目级 sub-agent 与运转 skill。

插件引导（clone / 绑定 git / automation）在公司市场仓：  
http://git.patsnap.com/patsnap/openai-plugins → `plugins/eng-agents`

## 目录

```text
.
├── .codex/
│   ├── agents/              # sub-agent（唯一源）
│   │   ├── coding.toml
│   │   └── security.toml
│   └── config.toml
├── .agents/skills/          # 仓库级运转 skill
│   ├── issue-pipeline/
│   └── security-review/
├── schemas/                 # .git_projects / automation 契约
├── AGENTS.md
└── README.md
```

## 使用

1. 安装插件：`codex plugin add eng-agents@patsnap-openai-plugins`
2. 运行 `$eng-agents-setup`（clone 本仓并配置）
3. 在 Codex 中打开并 **Trust** 本仓目录
4. `Spawn coding to …` / `$issue-pipeline`

## 扩展

- 新 sub-agent：在 `.codex/agents/` 增加 `*.toml`，并更新 `AGENTS.md`
- 新运转 skill：在 `.agents/skills/<name>/SKILL.md`
