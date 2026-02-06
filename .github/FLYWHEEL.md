# Flywheel Automation

本文件描述仓库自动化飞轮（GitHub Actions + Claude Code Action）的运行策略。

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
| `claude-code.yml` | 评论/手动 | 交互式 @claude 能力 |
| `ci.yml` | push / PR | lint + test + coverage |

## 核心策略

### 1) Issue 整理（Curation）

- 目标上限：`20`（可手动覆盖）
- 当 open issue 超过阈值时，优先关闭：低优先级且更旧的问题
- `frozen` 标签问题不参与自动关闭

### 2) 并行候选修复

- `fix.yml` 每次只选择 1 个待处理 issue
- 同时启动 3 个候选任务（`candidate 1/2/3`）
- 每个候选都必须：
  - 先补失败测试，再修复
  - 提交分支并创建 PR
  - PR 标题必须带统一前缀：
    - `[AUTOFIX][ISSUE-<id>][CANDIDATE-<n>]`

### 3) 独立 PR 仲裁与合并

- `merge-pr.yml` 按 issue 聚合候选 PR
- 默认至少 2 个候选且通过 checks 才触发仲裁
- 仲裁维度：
  - CI 结果
  - 修复完整性
  - 回归风险
  - 变更复杂度
- 只合并 1 个最佳候选；其余候选关闭并给出原因

### 4) CI 失败自愈

- 监听 `CI` workflow 失败事件
- 自动汇总失败 job 上下文并触发 Claude 修复
- 产出独立修复候选 PR，不直接改主分支

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

# 触发候选 PR 仲裁合并
gh workflow run merge-pr.yml

# 指定 issue 触发仲裁合并
gh workflow run merge-pr.yml -f issue_number=123

# 触发 CI 失败自动修复
gh workflow run ci-failure-auto-fix.yml
```

## 必要 Secrets

- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN`（Actions 默认注入）

## 保护建议

- 仓库保护规则要求 PR CI 通过后再合并
- 对 `master` 启用禁止直接 push
- 对自动化账号最小权限化
