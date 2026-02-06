"""Resolve merge-eligible candidate PRs for current flywheel run."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
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
    head = urllib.parse.quote(f"{owner}:{branch}", safe="")
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&head={head}&per_page=1"
    payload = _api_get(url, token)
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return first
    return None


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
    run_id = os.getenv("RUN_ID", "")
    output_file = os.getenv("GITHUB_OUTPUT", "")

    if not repo or not token or not issue_number or not run_id or not output_file:
        print("missing repository/token/issue_number/run_id/github_output", file=sys.stderr)
        return 2

    owner = repo.split("/", 1)[0]
    eligible_prs: list[int] = []

    for candidate_id in (1, 2, 3):
        branch = f"claude/issue-{issue_number}-candidate-{candidate_id}-{run_id}"
        pr = _find_open_pr_by_head(repo, owner, branch, token)
        if not pr:
            continue

        head = pr.get("head", {})
        sha = head.get("sha") if isinstance(head, dict) else None

        if not isinstance(sha, str):
            continue
        checks_ok = _status_checks_ok(repo, sha, token)
        if not _is_pr_candidate_eligible(pr, checks_ok):
            continue

        number = pr.get("number")
        assert isinstance(number, int)
        eligible_prs.append(number)

    eligible_csv = ",".join(str(n) for n in eligible_prs)
    if len(eligible_prs) < 2:
        _write_output(Path(output_file), {"should_merge": "false", "eligible_csv": eligible_csv})
        return 0

    _write_output(Path(output_file), {"should_merge": "true", "eligible_csv": eligible_csv})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
