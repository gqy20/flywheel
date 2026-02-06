---
name: flywheel-candidate-fix
description: Generate candidate fix PRs for one issue in this repository. Use when working on the 3-candidate fix model, TDD fix flow, and strict branch/PR naming conventions.
allowed-tools: Read,Grep,Glob,LS,Edit,MultiEdit,Write,Bash(git *),Bash(gh *),Bash(uv run pytest *),Bash(uv run ruff *)
---

# Flywheel Candidate Fix

## Goal

Produce a small, reviewable candidate PR that addresses one issue using TDD and project conventions.

## Workflow

1. Read issue details and target files.
2. RED: add/adjust a failing regression test for the issue.
3. GREEN: implement minimal fix to pass test.
4. Run targeted checks:
   - `uv run pytest ...`
   - `uv run ruff check ...`
5. Create candidate branch and PR with project naming convention:
   - Branch: `claude/issue-<id>-candidate-<n>-<run_id>`
   - PR title prefix: `[AUTOFIX][ISSUE-<id>][CANDIDATE-<n>]`
6. Include in PR body:
   - Summary
   - Tests run
   - Risks/limitations
   - `Closes #<id>` when appropriate

## Safety Rules

- Never push directly to `master`.
- Keep scope to one issue.
- Avoid workflow or secret changes.

## Output Checklist

- Test file(s) added/changed
- Source file(s) changed
- Commands executed
- PR URL
