# Automation Runbook

This runbook describes how to operate and recover Flywheel automation safely.

## Scope

- Workflows: `flywheel-orchestrator.yml`, `ci-failure-auto-fix.yml`, `automation-metrics.yml`, `docs-ci.yml`, `docs-auto-maintenance.yml`
- Main policy doc: `.github/FLYWHEEL.md`
- Generated workflow input reference: `docs/generated/workflow-inputs.md`

## Daily Checks

1. Check latest workflow runs:
   ```bash
   gh run list --limit 20
   ```
2. Check orchestrator, CI, and docs gates:
   ```bash
   gh run list --workflow flywheel-orchestrator.yml --limit 5
   gh run list --workflow ci.yml --limit 5
   gh run list --workflow docs-ci.yml --limit 5
   ```
3. Check automation metrics dashboard issue:
   ```bash
   gh issue list --state open --search '"[METRICS] Automation Health Dashboard" in:title'
   ```

## Incident Triage

### 1) Orchestrator repeatedly failing

1. Inspect latest failed run:
   ```bash
   gh run list --workflow flywheel-orchestrator.yml --limit 5
   gh run view <run-id> --log
   ```
2. Check the circuit-breaker reason in workflow summary.
3. If root cause is external/transient, wait for cooldown window.
4. If root cause is code/config, fix and push to `master`.

### 2) Candidate PR quality degraded

1. Raise quality threshold temporarily:
   ```bash
   gh workflow run flywheel-orchestrator.yml -f candidate_quality_min_score=80
   ```
2. Require strict scorecards for arbitration:
   ```bash
   gh workflow run flywheel-orchestrator.yml -f require_scorecard=true
   ```
3. Inspect candidate scorecard artifacts in candidate branches:
   - `.flywheel/scorecards/issue-<id>/candidate-<id>-<run>.json`

### 3) Token spend too high / too low

1. Override runtime budget on dispatch:
   ```bash
   gh workflow run flywheel-orchestrator.yml \
     -f stage_max_retries=4 \
     -f token_budget_chars=1500000 \
     -f stage_max_turns_json='{"triage":40,"plan":50,"implement":90,"verify":110,"finalize":45}'
   ```
2. Track impact using automation metrics snapshots.

## Recovery Procedures

### Pause auto-fix quickly

1. Use restrictive issue pool on manual run:
   ```bash
   gh workflow run flywheel-orchestrator.yml -f min_fixable_issues=999
   ```
2. Optionally disable schedule in `.github/workflows/flywheel-orchestrator.yml` via PR if sustained pause is needed.

### Manual merge path

1. Skip automated arbitration and merge vetted PR manually:
   ```bash
   gh pr view <pr-number>
   gh pr merge <pr-number> --squash --delete-branch
   ```
2. Close other candidates with explicit reasons.

## Documentation Maintenance

1. Regenerate workflow input docs after workflow edits:
   ```bash
   uv run python scripts/check_docs_sync.py --generate
   ```
2. Validate sync:
   ```bash
   uv run python scripts/check_docs_sync.py --check
   ```
3. Keep `.github/FLYWHEEL.md` aligned with policy and `README.md` aligned with operator entrypoints.
