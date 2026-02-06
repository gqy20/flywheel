# Flywheel Automation

本文件描述仓库自动化飞轮（GitHub Actions + Claude Agent SDK）的运行策略。

## 目标

- 控制 Issue 池规模，避免无限堆积
- 同一 Issue 并行生成多个修复候选 PR
- 通过独立仲裁流程选择并合并最优候选
- 禁止自动流程直接 push 到 `master`

## 工作流总览

| Workflow | 触发 | 作用 |
|---|---|---|
| `flywheel-orchestrator.yml` | 每小时 / 手动 | 统一执行 scan -> evaluate -> fix(candidates) -> merge -> curation |
| `ci-failure-auto-fix.yml` | 手动 | 针对指定 PR 的失败 CI 场景生成修复候选 PR |
| `automation-metrics.yml` | 每日 / 手动 | 汇总自动化健康指标并写入 dashboard discussion（失败时回退 issue） |
| `docs-ci.yml` | push / PR / 手动 | 文档质量门禁（Markdown lint、文档-Workflow 同步、文档更新策略） |
| `docs-auto-maintenance.yml` | 手动 | 使用 Claude 执行文档自动维护并生成 PR |
| `claude-code.yml` | 评论/手动 | 交互式 @claude 能力 |
| `ci.yml` | push / PR | lint + test + coverage |

## 核心策略

### 1) 单一编排链路

- 不再使用 `scan/evaluate/fix/merge-pr/issue-curation` 分散 workflow。
- 统一由 `flywheel-orchestrator.yml` 串行编排：
  - `circuit-breaker`
  - `scan`
  - `evaluate`
  - `select-issue`
  - `generate-candidates`（3 路矩阵并行）
  - `merge`
  - `curation`
  - `summary`
- 每阶段使用 `needs` 显式依赖，避免跨 workflow 状态漂移。
- 关键门控与选择逻辑由共享脚本承载，避免 YAML 内嵌大段 shell：
  - `scripts/shared/circuit_breaker.py`
  - `scripts/shared/select_issue.py`
  - `scripts/shared/select_merge_eligible.py`

### 2) Scan 去重指纹

- 扫描创建 issue 要求稳定指纹：`[fingerprint:<value>]`
- 扫描后自动去重：
  - 保留最早 issue 为 canonical
  - 自动关闭重复项并附注释

### 3) 并行候选修复 + 质量门

- 每轮只选择 1 个 issue 进入修复。
- 固定 3 个候选并行执行（candidate 1/2/3）。
- 每个候选 PR 都执行质量门（默认阈值 `70/100`）：
  - 改动规模
  - 测试触达迹象
  - PR 说明完整性
  - checks 状态
- 低于阈值自动关闭，减少低质量候选噪声。

### 4) 仲裁合并

- 仅对当前 run 的候选分支进行仲裁，避免跨轮干扰。
- 至少 2 个候选满足硬性条件（非 draft、checks 通过、非 dirty）才进入仲裁。
- 仲裁后只允许 1 个 winner 合并。
- winner 必须具备结构化评分卡（`arbiter-scorecard` JSON），并由 workflow 校验关键字段。

### 5) 熔断与冷却

- 主链路统一熔断门控（可通过 `workflow_dispatch` 覆盖参数）。
- 默认策略：阈值 `3`，冷却 `120m`。
- 冷却窗口内自动跳过，避免异常持续放大成本。

### 6) 文档维护门禁

- `docs-ci.yml` 包含 3 项检查：
  - Markdown 规范检查（`README.md`、`AGENTS.md`、`.github/FLYWHEEL.md`、`docs/**/*.md`）
  - 文档与 workflow 输入一致性检查（`scripts/check_docs_sync.py --check`）
  - PR 场景下，当 `scripts/` 或 `.github/workflows/` 变更时，要求同步更新文档
- workflow 输入参数索引文档由脚本自动生成：
  - `docs/generated/workflow-inputs.md`

## 人工触发命令

```bash
# 触发统一编排链路
gh workflow run flywheel-orchestrator.yml

# 覆盖编排参数（示例）
gh workflow run flywheel-orchestrator.yml \
  -f candidate_quality_min_score=80 \
  -f min_fixable_issues=3 \
  -f stage_max_retries=4 \
  -f token_budget_chars=1500000 \
  -f stage_max_turns_json='{"triage":40,"plan":50,"implement":90,"verify":110,"finalize":45}'

# 触发 CI 失败自动修复
gh workflow run ci-failure-auto-fix.yml

# 触发自动化指标汇总
gh workflow run automation-metrics.yml

# 触发文档质量门禁
gh workflow run docs-ci.yml

# 手动触发文档自动维护
gh workflow run docs-auto-maintenance.yml
```

## 必要 Secrets

- `ANTHROPIC_AUTH_TOKEN`
- `GITHUB_TOKEN`（Actions 默认注入）

## 保护建议

- 仓库保护规则要求 PR CI 通过后再合并
- 对 `master` 启用禁止直接 push
- 对自动化账号最小权限化
