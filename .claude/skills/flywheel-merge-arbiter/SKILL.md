---
name: Flywheel Merge Arbiter
description: Arbitrate multiple candidate PRs for the same issue and merge exactly one winner. Use when running merge-pr workflow or comparing AUTOFIX candidate PRs.
allowed-tools: Read,Grep,Glob,LS,Bash(gh pr:*),Bash(gh issue:*),Bash(git:*)
---

# Flywheel Merge Arbiter

## Goal

Choose and merge exactly one best candidate PR per issue after hard gates pass.

## Workflow

1. Collect candidate PRs for one issue from title prefix.
2. Hard filters first:
   - non-draft
   - checks green
   - merge state not dirty
3. Compare eligible candidates on:
   - correctness and issue coverage
   - regression risk
   - complexity and maintainability
4. Merge exactly one winner (prefer squash).
5. Comment winner rationale.
6. Comment and close non-winners.
7. If no safe winner, do not merge and comment issue with blockers.

## Safety Rules

- Never merge more than one candidate per issue.
- Never bypass failing required checks.
- Never force-merge.

## Output Checklist

- Eligible PR list
- Winner PR number + why
- Non-winner closure summary
- Any blockers
