# Workflow Inputs Reference

This file is auto-generated from `.github/workflows/*.yml`.
Run `uv run python scripts/check_docs_sync.py --generate` after workflow changes.

## `automation-metrics.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `window_days` | `false` | `7` | `string` | Lookback window (days) |

## `branch-cleanup.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `branch_prefix` | `false` | `claude/` | `string` | Remote branch prefix under origin/ |
| `dry_run` | `false` | `True` | `boolean` | Only report candidates without deleting |
| `min_age_hours` | `false` | `24` | `string` | Delete only branches older than this (hours) |

## `candidate-pr-hygiene.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `dry_run` | `false` | `True` | `boolean` | Only report close candidates without closing PRs |
| `keep_per_issue` | `false` | `1` | `string` | How many newest candidate PRs to keep per issue |
| `min_age_hours` | `false` | `12` | `string` | Only close duplicates older than this age (hours) |

## `ci-failure-auto-fix.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `circuit_cooldown_minutes` | `false` | `90` | `string` | Circuit breaker cooldown window (minutes) |
| `circuit_failure_threshold` | `false` | `3` | `string` | Circuit breaker consecutive failure threshold |
| `debug_logs` | `false` | `false` | `boolean` | Enable verbose SDK logs for troubleshooting |
| `pr_number` | `true` | `` | `string` | Specific PR number to auto-fix |

## `claude-code.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `prompt` | `true` | `` | `string` | Prompt for manual Claude run |

## `docs-auto-maintenance.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `debug_logs` | `false` | `false` | `boolean` | Enable verbose SDK logs for troubleshooting |

## `flywheel-orchestrator.yml`

| Input | Required | Default | Type | Description |
|---|---|---|---|---|
| `candidate_quality_min_score` | `false` | `70` | `string` | Minimum quality score required for candidate PR (0-100) |
| `circuit_cooldown_minutes` | `false` | `120` | `string` | Circuit breaker cooldown window (minutes) |
| `circuit_failure_threshold` | `false` | `3` | `string` | Circuit breaker consecutive failure threshold |
| `debug_logs` | `false` | `false` | `boolean` | Enable verbose SDK logs for troubleshooting |
| `issue_batch_size` | `false` | `3` | `string` | Number of highest-priority issues to process per run |
| `max_issues` | `false` | `5` | `string` | Max issues to create in one run |
| `max_open_issues` | `false` | `20` | `string` | Target max number of open issues for curation |
| `min_fixable_issues` | `false` | `3` | `string` | Minimum number of fixable open issues required before auto-fix runs |
| `require_scorecard` | `false` | `true` | `boolean` | Require structured candidate scorecard files before arbitration |
| `stage_max_retries` | `false` | `4` | `string` | Per-stage retry count for staged fix execution |
| `stage_max_turns_json` | `false` | `{"triage":40,"plan":50,"implement":90,"verify":110,"finalize":45}` | `string` | Optional JSON stage turn overrides, e.g. {"triage":15,"verify":35} |
| `target_dir` | `false` | `src` | `string` | Directory to scan |
| `token_budget_chars` | `false` | `1500000` | `string` | Response character budget per candidate run |
