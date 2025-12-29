---
name: fix-issue
description: 自动修复 GitHub issue（TDD 流程）
argument-hint: [issue-number]
allowed-tools: Bash(git:*, pytest, gh:*), Read, Edit, Write
model: sonnet
---

# 修复 Issue #$1

## 🔴 RED Phase - 编写失败测试

1. 查看 issue 详情：
!`gh issue view $1 --json title,body`

2. 读取目标文件（根据 issue 中的 "文件:" 字段）

3. 编写失败的测试用例

4. 运行测试确认失败：
!`pytest -v`

5. 提交测试：
!`git add .`
!`git commit -m "test: 添加失败测试 (issue #$1)"`

---

## 🟢 GREEN Phase - 实现功能

1. 修改源代码使测试通过

2. 运行测试确认通过：
!`pytest -v`

3. 提交修复：
!`git add .`
!`git commit -m "feat: 实现功能 (issue #$1)"`

---

## ✅ 完成修复

1. 推送到远程：
!`git push`

2. 关闭 issue：
!`gh issue close $1 --comment "修复已完成 ✅"`

---

修复完成！
