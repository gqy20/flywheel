# Claude Code Action 调研（2026-02-06）

本文聚焦 `anthropics/claude-code-action@v1` 在本仓库可直接落地的调用方式。

## 核心结论

- `claude-code-action@v1` 已是通用自动化入口，不只支持 `@claude` 评论触发，也支持 `workflow_dispatch`、Issue/PR 事件驱动和纯 prompt 自动化。
- 对“完整自动开发迭代”最直接的能力是：
  - 直接读写仓库文件并提交变更（结合 `contents: write`）
  - 在 PR/Issue 中交互式响应
  - 接收自定义 `prompt` 和 `claude_args`（含工具白名单、模型、max-turns 等）
  - 返回结构化输出（`structured_output`）用于后续 workflow 编排
  - 支持多云推理后端（Anthropic API / Bedrock / Vertex / Foundry）

## 可直接调用能力清单

1. 评论触发（`@claude`）

- 触发源：`issue_comment`、`pull_request_review_comment`、`pull_request_review`、`issues`
- 适合：开发者在具体上下文中让 Claude 执行修复、补测试、解释代码。

1. 手动触发（`workflow_dispatch`）

- 触发源：GitHub UI 手动输入 `prompt`
- 适合：一次性批处理任务、紧急修复、仓库级分析。

1. 自动 PR Review

- 触发源：`pull_request`（opened/synchronize/...）
- 可选：`track_progress: true` 跟踪进度评论。

1. CI 失败自动修复

- 触发源：`workflow_run`（上游 CI 失败）
- 模式：收集失败日志后将上下文注入 `prompt`，让 Claude 自动修复并推分支。

1. Issue 分流/打标

- 触发源：`issues: opened`
- 模式：用 prompt 调仓库内 slash command（如 `/label-issue`）执行分类。

## 关键输入参数（可直接用）

- `prompt`: 直接传任务指令（支持自动化模式）
- `claude_args`: 传 Claude CLI 参数（如 `--allowedTools`、`--max-turns`、`--model`）
- `settings`: JSON 字符串或文件路径，做高级配置
- `github_token`: 明确提供 GitHub token（建议）
- `anthropic_api_key`: 直连 Anthropic API 时必需
- `track_progress`: PR/Issue 处理中展示进度
- `allowed_non_write_users`: 允许非写权限用户触发（需谨慎）

## 输出（可直接接后续步骤）

- `execution_file`: Claude 执行日志文件路径
- `branch_name`: 本次运行生成的分支名
- `structured_output`: 结构化 JSON 输出（适合编排）
- `session_id`: 会话 ID，可用于续跑

## 与当前仓库的接入建议

1. 已新增 `.github/workflows/claude-code.yml`

- 支持 `@claude` 交互触发
- 支持 `workflow_dispatch` 直接输入 prompt 运行
- 默认工具白名单限制为本仓库常用命令（`git/gh/pytest/ruff`）

1. 建议短期策略

- 把 `scan/evaluate/fix` 先保留为计划内批处理链路
- 把高价值修复迁移到 `claude-code-action` 驱动（可观测、可复现、触发灵活）

1. 建议中期策略

- 将 issue 选择/排序逻辑从脚本层收敛到 workflow 编排层
- 统一由 Action 驱动修复执行，统一权限模型与运行日志格式

## 来源

- <https://github.com/anthropics/claude-code-action>
- <https://github.com/anthropics/claude-code-action/blob/main/action.yml>
- <https://github.com/anthropics/claude-code-action/tree/main/examples>
- <https://github.com/anthropics/claude-code-base-action>
