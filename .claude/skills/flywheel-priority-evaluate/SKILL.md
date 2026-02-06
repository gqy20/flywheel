---
name: flywheel-priority-evaluate
description: Re-evaluate and normalize issue priority labels (p0-p3) based on issue content and business impact.
allowed-tools: Read,Grep,Glob,LS,Bash(gh:*),Bash(git:*)
---

# Flywheel Priority Evaluate

## Goal

Ensure every open issue has exactly one priority label aligned with impact and urgency.

## Workflow

1. Read `.github/FLYWHEEL.md` and `.github/workflows/evaluate.yml`.
2. List open issues with title, body, and labels.
3. Re-evaluate each issue priority using repository rules:
   - `p0`: security/data-loss/blocker
   - `p1`: important bug/perf/core degradation
   - `p2`: normal bug/quality/test debt
   - `p3`: docs/refactor/low urgency
4. Normalize labels so each issue has exactly one of `p0|p1|p2|p3`.
5. Keep non-priority labels unchanged.

## Safety Rules

- Never remove non-priority labels unless user requests.
- Never assign multiple priority labels.
- Default uncertain cases to `p2`.

## Output Checklist

- Issues updated with old/new priority
- Distribution summary by priority
