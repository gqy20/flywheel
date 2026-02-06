"""Shared circuit-breaker gate for GitHub Actions workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class GateResult:
    should_run: bool
    reason: str


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _get_workflow_runs(
    repo: str, workflow_file: str, token: str, per_page: int = 30
) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs?per_page={per_page}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flywheel-circuit-breaker",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"failed to fetch workflow runs: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch workflow runs: {exc.reason}") from exc

    runs = payload.get("workflow_runs", [])
    if isinstance(runs, list):
        return [r for r in runs if isinstance(r, dict)]
    return []


def _evaluate_gate(
    runs: list[dict[str, Any]],
    current_run_id: int,
    failure_threshold: int,
    cooldown_minutes: int,
    now: datetime,
) -> GateResult:
    consecutive = 0
    last_failed_at: datetime | None = None

    for run in runs:
        run_id = run.get("id")
        status = run.get("status")
        conclusion = run.get("conclusion")
        updated_at = run.get("updated_at")

        if not isinstance(run_id, int) or run_id == current_run_id:
            continue
        if status != "completed":
            continue

        if conclusion == "failure":
            consecutive += 1
            if last_failed_at is None and isinstance(updated_at, str):
                last_failed_at = _parse_iso8601(updated_at)
            continue
        break

    if consecutive >= failure_threshold and last_failed_at is not None:
        elapsed_minutes = int((now - last_failed_at).total_seconds() // 60)
        if elapsed_minutes < cooldown_minutes:
            return GateResult(
                should_run=False,
                reason=f"cooldown_active_{elapsed_minutes}m_after_{consecutive}_failures",
            )

    return GateResult(should_run=True, reason="gate_open")


def _write_github_output(path: Path, result: GateResult) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(f"should_run={'true' if result.should_run else 'false'}\n")
        f.write(f"reason={result.reason}\n")


def _workflow_file_from_env() -> str:
    ref = os.getenv("GITHUB_WORKFLOW_REF", "")
    # Example: owner/repo/.github/workflows/file.yml@refs/heads/master
    base = ref.split("@", 1)[0]
    return base.rsplit("/", 1)[-1] if base else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--workflow-file", default=_workflow_file_from_env())
    parser.add_argument("--current-run-id", type=int, default=int(os.getenv("GITHUB_RUN_ID", "0")))
    parser.add_argument("--failure-threshold", type=int, required=True)
    parser.add_argument("--cooldown-minutes", type=int, required=True)
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("missing GH_TOKEN or GITHUB_TOKEN", file=sys.stderr)
        return 2
    if not args.repo:
        print("missing repository (pass --repo or set GITHUB_REPOSITORY)", file=sys.stderr)
        return 2
    if not args.workflow_file:
        print(
            "missing workflow file (pass --workflow-file or set GITHUB_WORKFLOW_REF)",
            file=sys.stderr,
        )
        return 2
    if args.current_run_id <= 0:
        print("missing/invalid current run id", file=sys.stderr)
        return 2

    runs = _get_workflow_runs(args.repo, args.workflow_file, token)
    result = _evaluate_gate(
        runs=runs,
        current_run_id=args.current_run_id,
        failure_threshold=args.failure_threshold,
        cooldown_minutes=args.cooldown_minutes,
        now=datetime.now(UTC),
    )

    if args.github_output:
        _write_github_output(Path(args.github_output), result)

    print(json.dumps({"should_run": result.should_run, "reason": result.reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
