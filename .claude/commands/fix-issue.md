---
name: fix-issue
description: 自动修复 GitHub issue（TDD 流程）
argument-hint: [issue-number]
allowed-tools: Bash(git:*, pytest, gh:*), Read, Edit, Write
model: sonnet
---

# 修复 Issue #$1

你是一个遵循 TDD（测试驱动开发）流程的开发者。请按照以下步骤修复这个 issue：

## 🔴 RED Phase - 编写失败测试

Issue 详情：
!`gh issue view $1 --json title,body`

### 步骤：

1. **查看 issue 详情**（已在上方提供）

2. **读取目标文件** - 使用 Read 工具读取 issue 中 "文件:" 字段指定的文件

3. **编写失败的测试用例** - 使用 Write 工具在 tests/ 目录下创建测试文件

4. **运行测试确认失败** - 使用 Bash 工具执行：`pytest -v`

5. **提交测试** - 使用 Bash 工具执行：
   - `git add .`
   - `git commit -m "test: 添加失败测试 (issue #$1)"`

---

## 🟢 GREEN Phase - 实现功能

### 步骤：

1. **修改源代码使测试通过** - 使用 Edit 或 Write 工具修改源代码

2. **运行测试确认通过** - 使用 Bash 工具执行：`pytest -v`

3. **提交修复** - 使用 Bash 工具执行：
   - `git add .`
   - `git commit -m "feat: 实现功能 (issue #$1)"`

---

## ✅ 完成修复

### 步骤：

1. **推送到主分支** - 使用 Bash 工具执行：`git push`

2. **关闭 issue** - 使用 Bash 工具执行：`gh issue close $1 --comment "修复已完成 ✅"`

---

## 重要提示

- **必须使用工具**：Read、Write、Edit、Bash 来完成任务
- **不要跳过步骤**：严格按照 TDD 流程执行
- **测试必须先失败**：RED phase 的测试必须失败才能继续
- **确保测试通过**：GREEN phase 完成后所有测试必须通过

修复完成！
