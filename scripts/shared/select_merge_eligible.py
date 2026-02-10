"""Resolve merge-eligible candidate PRs for current flywheel run.

This script finds all open candidate PRs for an issue (across all RUN_IDs),
not just the current run. This fixes the issue where old candidates were
orphaned and never considered for merge.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_CHECK_CONCLUSIONS = {"success", "neutral", "skipped"}


def _api_get(url: str, token: str, accept: str = "application/vnd.github+json") -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flywheel-merge-eligible",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API error: HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API unreachable: {exc.reason}") from exc


def _find_open_pr_by_head(repo: str, owner: str, branch: str, token: str) -> dict[str, Any] | None:
    """Legacy function: find PR by exact branch name (only works for current RUN_ID)."""
    head = urllib.parse.quote(f"{owner}:{branch}", safe="")
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&head={head}&per_page=1"
    payload = _api_get(url, token)
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return first
    return None


def _find_all_candidate_prs(repo: str, issue_number: str, token: str) -> list[dict[str, Any]]:
    """Find all open candidate PRs for an issue across ALL RUN_IDs.

    Uses GitHub Search API to find PRs with title matching the candidate pattern.
    This ensures we don't orphan candidates from previous runs.
    """
    # Search for PRs with title containing the issue prefix
    query = f'repo:{repo} is:pr is:open "[AUTOFIX][ISSUE-{issue_number}]" in:title sort:created-asc'
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}&per_page=50"

    try:
        payload = _api_get(url, token)
    except RuntimeError as e:
        print(f"Warning: Search API failed: {e}, falling back to branch iteration", file=sys.stderr)
        return _find_all_candidates_via_branches(repo, issue_number, token)

    if not isinstance(payload, dict):
        return []

    items = payload.get("items", [])
    if not isinstance(items, list):
        return []

    # Filter to PRs that match our branch pattern
    candidates: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Get full PR details
        pr_url = item.get("pull_request", {}).get("url", "")
        if not pr_url:
            continue

        # Fetch full PR details
        try:
            full_pr = _api_get(pr_url, token)
        except RuntimeError:
            continue

        if not isinstance(full_pr, dict):
            continue

        # Validate it has a valid candidate branch pattern
        head_ref = full_pr.get("headRefName", "")
        if _is_valid_candidate_branch(head_ref, issue_number):
            candidates.append(full_pr)

    return candidates


def _find_all_candidates_via_branches(
    repo: str, issue_number: str, token: str
) -> list[dict[str, Any]]:
    """Fallback: iterate through all branches to find candidate PRs.

    This is less efficient but works when Search API is unavailable.
    """
    owner = repo.split("/", 1)[0]
    candidates: list[dict[str, Any]] = []

    # List all branches matching the pattern
    url = f"https://api.github.com/repos/{repo}/branches?per_page=100"
    try:
        branches = _api_get(url, token)
    except RuntimeError:
        return []

    if not isinstance(branches, list):
        return []

    for branch in branches:
        if not isinstance(branch, dict):
            continue
        branch_name = branch.get("name", "")
        if _is_valid_candidate_branch(branch_name, issue_number):
            # Find PR for this branch
            pr = _find_open_pr_by_head(repo, owner, branch_name, token)
            if pr and pr not in candidates:
                candidates.append(pr)

    return candidates


def _is_valid_candidate_branch(branch_name: str, issue_number: str) -> bool:
    """Check if branch matches claude/issue-{issue}-candidate-{n}-{run_id} pattern."""
    if not isinstance(branch_name, str):
        return False
    pattern = f"claude/issue-{issue_number}-candidate-"
    if not branch_name.startswith(pattern):
        return False
    # Extract candidate number and verify format
    suffix = branch_name[len(pattern) :]
    parts = suffix.rsplit("-", 1)
    if len(parts) != 2:
        return False
    try:
        candidate_num = int(parts[0])
        return 1 <= candidate_num <= 3
    except ValueError:
        return False


def _get_pr_age_days(pr: dict[str, Any]) -> float:
    """Calculate age of PR in days."""
    created_at = pr.get("createdAt", "")
    if not created_at:
        return 0.0
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        delta = now - created
        return delta.total_seconds() / 86400
    except ValueError:
        return 0.0


def _status_checks_ok(repo: str, sha: str, token: str) -> bool:
    status_url = f"https://api.github.com/repos/{repo}/commits/{sha}/status"
    status_payload = _api_get(status_url, token)
    total_status = (
        int(status_payload.get("total_count", 0)) if isinstance(status_payload, dict) else 0
    )
    state = status_payload.get("state") if isinstance(status_payload, dict) else None

    if total_status > 0 and state != "success":
        return False

    checks_url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100"
    checks_payload = _api_get(checks_url, token)
    if not isinstance(checks_payload, dict):
        return True

    total_checks = int(checks_payload.get("total_count", 0))
    if total_checks == 0:
        return True

    check_runs = checks_payload.get("check_runs", [])
    if not isinstance(check_runs, list):
        return False

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


def _is_pr_candidate_eligible(pr: dict[str, Any], checks_ok: bool) -> bool:
    number = pr.get("number")
    draft = pr.get("draft")
    merge_state = str(pr.get("mergeable_state", "")).lower()
    head = pr.get("head", {})
    sha = head.get("sha") if isinstance(head, dict) else None

    if not isinstance(number, int) or not isinstance(draft, bool) or not isinstance(sha, str):
        return False
    if draft:
        return False
    if merge_state == "dirty":
        return False
    return checks_ok


def _write_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")


def main() -> int:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    issue_number = os.getenv("ISSUE_NUMBER", "")
    run_id = os.getenv("RUN_ID", "")  # Kept for backward compatibility, not used for filtering
    output_file = os.getenv("GITHUB_OUTPUT", "")
    min_candidates = int(os.getenv("MIN_CANDIDATES_FOR_ARBITRATION", "1"))

    if not repo or not token or not issue_number or not output_file:
        print("missing repository/token/issue_number/github_output", file=sys.stderr)
        return 2

    # Find ALL candidate PRs across all RUN_IDs (fixes orphan issue)
    all_candidates = _find_all_candidate_prs(repo, issue_number, token)

    if not all_candidates:
        print(f"No candidate PRs found for issue #{issue_number}")
        _write_output(Path(output_file), {"should_merge": "false", "eligible_csv": ""})
        return 0

    print(f"Found {len(all_candidates)} candidate PRs for issue #{issue_number}")

    # Check eligibility and CI status for each candidate
    eligible_prs: list[int] = []
    eligible_details: list[dict] = []

    for pr in all_candidates:
        head = pr.get("head", {})
        sha = head.get("sha") if isinstance(head, dict) else None

        if not isinstance(sha, str):
            continue

        # Check CI status
        try:
            checks_ok = _status_checks_ok(repo, sha, token)
        except RuntimeError:
            checks_ok = False

        if not _is_pr_candidate_eligible(pr, checks_ok):
            continue

        number = pr.get("number")
        if not isinstance(number, int):
            continue

        eligible_prs.append(number)
        eligible_details.append(
            {
                "pr": number,
                "branch": pr.get("headRefName", ""),
                "age_days": _get_pr_age_days(pr),
                "checks_ok": checks_ok,
            }
        )

    eligible_csv = ",".join(str(n) for n in eligible_prs)

    if len(eligible_prs) < min_candidates:
        print(f"Insufficient eligible candidates: {len(eligible_prs)} < {min_candidates}")
        if eligible_details:
            print("Eligible but not enough:")
            for d in eligible_details:
                print(f"  PR #{d['pr']}: branch={d['branch']}, age={d['age_days']:.1f}d")
        _write_output(
            Path(output_file),
            {
                "should_merge": "false",
                "eligible_csv": eligible_csv,
                "total_found": str(len(all_candidates)),
                "eligible_count": str(len(eligible_prs)),
            },
        )
        return 0

    print(f"Arbitration ready: {len(eligible_prs)} eligible candidates")
    for d in eligible_details:
        print(f"  PR #{d['pr']}: {d['branch']}")

    _write_output(
        Path(output_file),
        {
            "should_merge": "true",
            "eligible_csv": eligible_csv,
            "total_found": str(len(all_candidates)),
            "eligible_count": str(len(eligible_prs)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
