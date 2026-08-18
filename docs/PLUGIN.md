# Plugin 开发与分发

产品实现在 **本 GitHub 仓**；PatSnap 内部分发通过 GitLab 市场 [`openai-plugins`](http://git.patsnap.com/patsnap/openai-plugins) 的 **git-subdir 指针**，不拷贝代码。

插件 id：`engineering-agents@openai-plugins`

## 结构

```text
plugins/engineering-agents/
  .codex-plugin/plugin.json
  skills/<name>/SKILL.md
  agents/*.toml
  config/managed-manifest.json
  scripts/
```

## 用户安装（PatSnap 市场）

```bash
codex plugin marketplace add git@git.patsnap.com:patsnap/openai-plugins.git
codex plugin add engineering-agents@openai-plugins
bash plugins/engineering-agents/scripts/install.sh    # ~/.codex/agents
```

项目级：

```bash
bash install.sh --into /path/to/repo
```

## 市场仓条目（GitLab，不在本仓）

`openai-plugins/.agents/plugins/marketplace.json`：

```json
{
  "name": "engineering-agents",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/guxiaolong-patsnap/codex-engineering-agents.git",
    "path": "./plugins/engineering-agents",
    "ref": "main"
  }
}
```

## 开发本仓

```bash
./scripts/sync-local-dev.sh
# 改 agents 后 reinstall 或 sync
bash plugins/engineering-agents/scripts/install-project.sh --dry-run --into .
```

## 升级

```bash
codex plugin marketplace upgrade openai-plugins
codex plugin upgrade engineering-agents@openai-plugins
bash plugins/engineering-agents/scripts/install.sh
```

项目级：对业务仓重跑 `install.sh --into …`。
