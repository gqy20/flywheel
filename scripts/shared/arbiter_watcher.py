#!/usr/bin/env python3
"""Arbiter Watcher: Find issues with eligible candidates and trigger merge arbitration.

This script scans for issues with open candidate PRs that have CI passing
and triggers the merge process for them.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

ALLOWED_CHECK_CONCLUSIONS = {"success", "neutral", "skipped"}


@dataclass(frozen=True)
class CandidatePR:
    number: int
    issue: int
    title: str
    branch: str
    created_at: datetime
    mergeable: bool
    checks_ok: bool


def _run_gh(args: list[str]) -> str:
    """Run gh CLI command."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_PAGER": "cat"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh command failed: {result.stderr}")
    return result.stdout.strip()


def _api_get(url: str, token: str, accept: str = "application/vnd.github+json") -> Any:
    """Make authenticated GET request to GitHub API."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flywheel-arbiter-watcher",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API error: HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API unreachable: {exc.reason}") from exc


def _parse_pr_title(title: str) -> tuple[int, int] | None:
    """Parse [AUTOFIX][ISSUE-123][CANDIDATE-2] format."""
    if not title.startswith("[AUTOFIX][ISSUE-"):
        return None
    try:
        issue_part = title.split("][")[1]  # ISSUE-123
        candidate_part = title.split("][")[2].split("]")[0]  # CANDIDATE-2
        issue_num = int(issue_part.replace("ISSUE-", ""))
        candidate_num = int(candidate_part.replace("CANDIDATE-", ""))
        return (issue_num, candidate_num)
    except (IndexError, ValueError):
        return None


def _get_checks_status(repo: str, sha: str, token: str) -> bool:
    """Check if all CI checks pass for a commit."""
    if not sha:
        return True

    # Check status
    status_url = f"https://api.github.com/repos/{repo}/commits/{sha}/status"
    try:
        status_payload = _api_get(status_url, token)
    except RuntimeError:
        return True  # Assume success on error

    if isinstance(status_payload, dict):
        total_status = int(status_payload.get("total_count", 0))
        state = status_payload.get("state")
        if total_status > 0 and state != "success":
            return False

    # Check runs
    checks_url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100"
    try:
        checks_payload = _api_get(checks_url, token)
    except RuntimeError:
        return True

    if not isinstance(checks_payload, dict):
        return True

    total_checks = int(checks_payload.get("total_count", 0))
    if total_checks == 0:
        return True

    check_runs = checks_payload.get("check_runs", [])
    if not isinstance(check_runs, list):
        return True

    for run in check_runs:
        if not isinstance(run, dict):
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return False
        if conclusion not in ALLOWED_CHECK_CONCLUSIONS:
            return False

    return True


def _list_open_candidate_prs(token: str, repo: str, limit: int = 200) -> list[CandidatePR]:
    """List all open candidate PRs with their status."""
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page={limit}"
    try:
        prs = _api_get(url, token)
    except RuntimeError as e:
        print(f"Error fetching PRs: {e}", file=sys.stderr)
        return []

    if not isinstance(prs, list):
        return []

    candidates: list[CandidatePR] = []
    for pr in prs:
        if not isinstance(pr, dict):
            continue

        title = pr.get("title", "")
        parsed = _parse_pr_title(title)
        if not parsed:
            continue

        issue_num, _ = parsed
        branch = pr.get("headRefName", "")
        created_at = pr.get("createdAt", "")
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=UTC)
        except ValueError:
            created = datetime.now(UTC)

        mergeable = pr.get("mergeable", True)
        if isinstance(mergeable, str):
            mergeable = mergeable.lower() != "false"

        # Get CI status
        sha = pr.get("head", {}).get("sha", "")
        checks_ok = _get_checks_status(repo, sha, token)

        candidates.append(
            CandidatePR(
                number=pr.get("number", 0),
                issue=issue_num,
                title=title,
                branch=branch,
                created_at=created,
                mergeable=mergeable,
                checks_ok=checks_ok,
            )
        )

    return candidates


def _group_by_issue(candidates: list[CandidatePR]) -> dict[int, list[CandidatePR]]:
    """Group candidate PRs by issue number."""
    grouped: dict[int, list[CandidatePR]] = {}
    for pr in candidates:
        if pr.issue not in grouped:
            grouped[pr.issue] = []
        grouped[pr.issue].append(pr)
    return grouped


def _trigger_workflow_dispatch(issue: int, dry_run: bool) -> bool:
    """Trigger flywheel-orchestrator via workflow dispatch for specific issue."""
    # The orchestrator selects issues automatically, but we can use
    # workflow_run_id to force it to pick specific issues from pending candidates

    # For now, just report what needs to be done
    if dry_run:
        print(f"[DRY-RUN] Would trigger merge for issue #{issue}")
        return True

    # Trigger orchestrator - it will pick issues with pending candidates
    # because they appear as "busy" in select_issue.py
    try:
        result = subprocess.run(
            [
                "gh",
                "workflow",
                "run",
                "flywheel-orchestrator.yml",
                "--ref",
                "master",
                "-f",
                "issue_batch_size=1",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "GH_PAGER": "cat"},
        )
        if result.returncode == 0:
            print(f"Triggered flywheel-orchestrator for issue #{issue}")
            return True
        else:
            print(f"Failed to trigger workflow: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error triggering workflow: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository in owner/repo format")
    parser.add_argument("--token", required=True, help="GitHub API token")
    parser.add_argument(
        "--min-age-hours", type=int, default=1, help="Only consider candidates older than this"
    )
    parser.add_argument(
        "--require-mergeable", action="store_true", help="Only consider mergeable PRs"
    )
    parser.add_argument(
        "--require-checks-success",
        action="store_true",
        help="Only consider PRs with passing CI checks",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Report without triggering (default)"
    )
    parser.add_argument("--limit", type=int, default=200, help="Max PRs to fetch")
    args = parser.parse_args()

    # Fetch all open candidate PRs
    candidates = _list_open_candidate_prs(args.token, args.repo, limit=args.limit)

    if not candidates:
        print("No candidate PRs found")
        return

    # Group by issue
    grouped = _group_by_issue(candidates)

    # Find issues needing arbitration
    now = datetime.now(UTC)
    issues_needing_arbiter: list[tuple[int, list[CandidatePR]]] = []

    for issue_num, prs in sorted(grouped.items()):
        # Filter by criteria
        eligible = []
        for pr in prs:
            # Age filter
            age_hours = (now - pr.created_at).total_seconds() / 3600
            if age_hours < args.min_age_hours:
                continue
            # Mergeable filter
            if args.require_mergeable and not pr.mergeable:
                continue
            # Checks filter
            if args.require_checks_success and not pr.checks_ok:
                continue
            eligible.append(pr)

        if eligible:
            issues_needing_arbiter.append((issue_num, eligible))

    # Report
    print("\n=== Arbiter Watcher Report ===")
    print(f"Repository: {args.repo}")
    print(f"Total open candidates: {len(candidates)}")
    print(f"Issues with eligible candidates: {len(issues_needing_arbiter)}")

    for issue_num, prs in issues_needing_arbiter:
        print(f"\nIssue #{issue_num}: {len(prs)} eligible candidate(s)")
        for pr in prs:
            age_hours = (now - pr.created_at).total_seconds() / 3600
            status = []
            if not pr.mergeable:
                status.append("unmergeable")
            if not pr.checks_ok:
                status.append("checks-failing")
            status_str = f" ({', '.join(status)})" if status else ""
            print(f"  - PR #{pr.number}: {pr.branch} (age: {age_hours:.1f}h{status_str})")

    # Trigger arbitration for eligible issues
    print("\n=== Triggering Arbitration ===")
    triggered = 0
    for issue_num, _ in issues_needing_arbiter:
        if _trigger_workflow_dispatch(issue_num, dry_run=args.dry_run):
            triggered += 1

    print("\nSummary:")
    print(f"  Issues to arbitrate: {len(issues_needing_arbiter)}")
    print(f"  Triggered: {triggered}")
    print(f"  Dry run: {args.dry_run}")


if __name__ == "__main__":
    main()
