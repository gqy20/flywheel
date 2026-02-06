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
   - correctness and issue coverage (weight 0.45)
   - regression risk (weight 0.30)
   - complexity and maintainability (weight 0.15)
   - test quality and verification evidence (weight 0.10)
4. Compute weighted total score and rank candidates.
5. Post machine-readable scorecard before merge:
   - Marker line: `<!-- arbiter-scorecard -->`
   - Next line must be one-line JSON:
     `{"issue":<id>,"winner_pr":<id>,"scores":[...]}`
6. Include per-candidate scores for correctness, risk, maintainability, tests, total, verdict, reason.
7. Merge exactly one winner (prefer squash).
8. Comment and close non-winners.
9. If no safe winner, do not merge and comment issue with blockers.

## Safety Rules

- Never merge more than one candidate per issue.
- Never bypass failing required checks.
- Never force-merge.

## Output Checklist

- Eligible PR list
- Winner PR number + why
- Non-winner closure summary
- Any blockers
