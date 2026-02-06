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
| `scan.yml` | 每小时 / 手动 | 扫描代码并创建问题 Issue |
| `evaluate.yml` | 每小时 + issue 事件 | 重算优先级标签 |
| `issue-curation.yml` | 每小时 / 手动 | 将 open issue 控制在阈值内（默认 20） |
| `fix.yml` | 每小时 / 手动 | 选择一个 issue，启动 3 路并行候选修复并提交 PR |
| `merge-pr.yml` | 每小时 / 手动 | 对同一 issue 的候选 PR 做硬性 checks 过滤后仲裁合并 |
| `ci-failure-auto-fix.yml` | CI 失败时 / 手动 | 针对失败 CI 自动生成修复候选 PR |
| `automation-metrics.yml` | 每日 / 手动 | 汇总自动化健康指标并写入 dashboard issue |
| `claude-code.yml` | 评论/手动 | 交互式 @claude 能力 |
| `ci.yml` | push / PR | lint + test + coverage |

## 核心策略

### 1) Issue 整理（Curation）

- 目标上限：`20`（可手动覆盖）
- 当 open issue 超过阈值时，优先关闭：低优先级且更旧的问题
- `frozen` 标签问题不参与自动关闭

### 1.5) Scan 去重指纹

- `scan.yml` 生成 issue 时要求包含稳定指纹：`[fingerprint:<value>]`
- 扫描后会自动对 open issues 做指纹去重：
  - 保留最早 issue 作为 canonical
  - 自动关闭重复项并附注释

### 2) 并行候选修复

- `fix.yml` 每次只选择 1 个待处理 issue
- 同时启动 3 个候选任务（`candidate 1/2/3`）
- 每个候选都必须：
  - 先补失败测试，再修复
  - 提交分支并创建 PR
  - PR 标题必须带统一前缀：
    - `[AUTOFIX][ISSUE-<id>][CANDIDATE-<n>]`
- 候选 PR 创建后立即走质量门（默认阈值 `70/100`）：
  - 对改动规模、测试覆盖迹象、PR 说明完整性、检查状态进行打分
  - 低于阈值自动关闭，避免低质量候选进入仲裁

### 3) 独立 PR 仲裁与合并

- `merge-pr.yml` 按 issue 聚合候选 PR
- 默认至少 2 个候选且通过 checks 才触发仲裁
- 仲裁维度：
  - 修复完整性（0.45）
  - 回归风险（0.30）
  - 变更复杂度与可维护性（0.15）
  - 测试质量与验证证据（0.10）
- 只合并 1 个最佳候选；其余候选关闭并给出原因
- 仲裁输出要求结构化评分卡（`arbiter-scorecard` JSON），workflow 会自动校验格式和关键字段

### 4) 失败熔断与冷却

- `scan/evaluate/issue-curation/fix/merge-pr/ci-failure-auto-fix` 都启用统一熔断门控
- 默认策略（可在 `workflow_dispatch` 用参数覆盖）：
  - `scan`: 阈值 `4`，冷却 `90m`
  - `evaluate`: 阈值 `4`，冷却 `90m`
  - `issue-curation`: 阈值 `4`，冷却 `60m`
  - `fix`: 阈值 `3`，冷却 `120m`
  - `merge-pr`: 阈值 `2`，冷却 `90m`
  - `ci-failure-auto-fix`: 阈值 `3`，冷却 `90m`
- 在冷却窗口内自动跳过本轮运行，避免异常时持续放大噪音和成本

### 5) CI 失败自愈

- 监听 `CI` workflow 失败事件
- 自动汇总失败 job 上下文并触发 Claude 修复
- 产出独立修复候选 PR，不直接改主分支

### 6) Claude Skills 显式接入

- 本仓库将技能定义放在 `.claude/skills/`
- `scan.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-scan-issues/SKILL.md`
- `evaluate.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-priority-evaluate/SKILL.md`
- `issue-curation.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-issue-curation/SKILL.md`
- `fix.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-candidate-fix/SKILL.md`
- `merge-pr.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-merge-arbiter/SKILL.md`
- `ci-failure-auto-fix.yml` 在 prompt 中显式加载：
  - `.claude/skills/flywheel-ci-failure-autofix/SKILL.md`

## 人工触发命令

```bash
# 触发扫描
gh workflow run scan.yml

# 触发优先级评估
gh workflow run evaluate.yml

# 触发 issue 整理（默认上限 20）
gh workflow run issue-curation.yml

# 触发并行修复候选（自动选 issue）
gh workflow run fix.yml

# 指定 issue 触发并行修复候选
gh workflow run fix.yml -f issue_number=123

# 指定 issue 且覆盖候选质量门阈值
gh workflow run fix.yml -f issue_number=123 -f candidate_quality_min_score=80

# 临时覆盖熔断参数（示例）
gh workflow run fix.yml -f issue_number=123 -f circuit_failure_threshold=5 -f circuit_cooldown_minutes=30

# 触发候选 PR 仲裁合并
gh workflow run merge-pr.yml

# 指定 issue 触发仲裁合并
gh workflow run merge-pr.yml -f issue_number=123

# 触发 CI 失败自动修复
gh workflow run ci-failure-auto-fix.yml

# 触发自动化指标汇总
gh workflow run automation-metrics.yml
```

## 必要 Secrets

- `ANTHROPIC_AUTH_TOKEN`
- `GITHUB_TOKEN`（Actions 默认注入）

## 保护建议

- 仓库保护规则要求 PR CI 通过后再合并
- 对 `master` 启用禁止直接 push
- 对自动化账号最小权限化
