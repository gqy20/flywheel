---
name: flywheel-issue-curation
description: Curate GitHub issues for this repository. Use when user asks to control open issue count, clean backlog, enforce p0-p3/frozen priority strategy, or batch-close low-priority stale issues.
allowed-tools: Read,Grep,Glob,LS,Bash(gh *),Bash(git *)
---

# Flywheel Issue Curation

## Goal

Keep issue pool healthy and bounded, with explicit priority handling and safe bulk operations.

## Workflow

1. Read `.github/FLYWHEEL.md` and `.github/workflows/issue-curation.yml` first.
2. Fetch open issues and labels with `gh issue list --json ...`.
3. Compute target delta from configured cap (default 20).
4. Exclude `frozen` and security-critical items unless user explicitly requests otherwise.
5. Prefer closing oldest low-priority issues (`p3` -> `p2` -> unlabeled).
6. Add a clear close comment that explains curation policy and reopen path.
7. Summarize how many were closed and why.

## Safety Rules

- Never delete issues by default.
- Never close `frozen` issues automatically.
- Never alter labels unrelated to priority without explicit user request.

## Output Checklist

- Open issue count before/after
- Closed issue numbers
- Policy rationale used
