---
name: Flywheel CI Failure Autofix
description: Investigate failed CI runs and create a dedicated fix PR. Use when CI workflow fails, when user asks to auto-fix failing checks, or when analyzing job logs for minimal corrective changes.
allowed-tools: Read,Grep,Glob,LS,Edit,MultiEdit,Write,Bash(gh api:*),Bash(gh pr:*),Bash(git:*),Bash(uv run pytest:*),Bash(uv run ruff:*)
---

# Flywheel CI Failure Autofix

## Goal

Turn a failed CI run into a focused repair PR with root-cause explanation.

## Workflow

1. Fetch failed workflow run and job summaries.
2. Identify primary failing check and minimal fix path.
3. Implement targeted code/test fix.
4. Re-run affected checks locally where possible.
5. Create fix branch and PR with CI-fail prefix.
6. Document in PR body:
   - probable root cause
   - fix summary
   - verification commands
   - residual risks

## Safety Rules

- Do not touch unrelated modules.
- Do not edit workflow permissions/secrets unless explicitly requested.
- Do not push directly to `master`.

## Output Checklist

- Failed job(s) analyzed
- Root-cause statement
- Files changed
- Verification commands
- PR URL
