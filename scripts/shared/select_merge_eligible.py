"""Resolve merge-eligible candidate PRs for current flywheel run."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ALLOWED_CHECK_CONCLUSIONS = {"success", "neutral", "skipped"}
BRANCH_PATTERN = re.compile(
    r"^claude/issue-(?P<issue>\d+)-candidate-(?P<candidate>\d+)-(?P<run>\d+)$"
)


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


def _parse_candidate_branch(branch: str) -> tuple[int, int, int] | None:
    match = BRANCH_PATTERN.match(branch)
    if not match:
        return None
    return (int(match.group("issue")), int(match.group("candidate")), int(match.group("run")))


def _list_open_issue_candidate_prs(repo: str, issue_number: str, token: str) -> list[dict[str, Any]]:
    issue_int = int(issue_number)
    page = 1
    per_page = 100
    selected: list[dict[str, Any]] = []
    while True:
        url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page={per_page}&page={page}"
        payload = _api_get(url, token)
        if not isinstance(payload, list) or not payload:
            break

        for item in payload:
            if not isinstance(item, dict):
                continue
            head = item.get("head")
            if not isinstance(head, dict):
                continue
            ref = head.get("ref")
            if not isinstance(ref, str):
                continue
            parsed = _parse_candidate_branch(ref)
            if parsed is None:
                continue
            parsed_issue, parsed_candidate, _ = parsed
            if parsed_issue != issue_int:
                continue
            if parsed_candidate not in {1, 2, 3}:
                continue
            selected.append(item)

        if len(payload) < per_page:
            break
        page += 1

    return selected


def _pick_latest_per_candidate(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[int, dict[str, Any]] = {}
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        head = pr.get("head")
        if not isinstance(head, dict):
            continue
        ref = head.get("ref")
        if not isinstance(ref, str):
            continue
        parsed = _parse_candidate_branch(ref)
        if parsed is None:
            continue
        _, candidate_id, _ = parsed
        current = latest.get(candidate_id)
        if current is None:
            latest[candidate_id] = pr
            continue
        pr_updated = str(pr.get("updated_at", ""))
        current_updated = str(current.get("updated_at", ""))
        if pr_updated >= current_updated:
            latest[candidate_id] = pr
    return [latest[cid] for cid in sorted(latest)]


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
    candidate_pool: list[dict[str, Any]] = []
    seen_numbers: set[int] = set()
    for candidate_id in (1, 2, 3):
        branch = f"claude/issue-{issue_number}-candidate-{candidate_id}-{run_id}"
        pr = _find_open_pr_by_head(repo, owner, branch, token)
        if not pr:
            continue
        number = pr.get("number")
        if not isinstance(number, int):
            continue
        if number in seen_numbers:
            continue
        candidate_pool.append(pr)
        seen_numbers.add(number)

    # Fallback to cross-run candidates for this issue to avoid stale backlog when
    # current run cannot provide >=2 eligible candidates.
    if len(candidate_pool) < 2:
        for pr in _pick_latest_per_candidate(_list_open_issue_candidate_prs(repo, issue_number, token)):
            number = pr.get("number")
            if not isinstance(number, int):
                continue
            if number in seen_numbers:
                continue
            candidate_pool.append(pr)
            seen_numbers.add(number)

    eligible_prs: list[int] = []
    for pr in candidate_pool:
        head = pr.get("head", {})
        sha = head.get("sha") if isinstance(head, dict) else None

        if not isinstance(sha, str):
            continue
        checks_ok = _status_checks_ok(repo, sha, token)
        if not _is_pr_candidate_eligible(pr, checks_ok):
            continue

        number = pr.get("number")
        if not isinstance(number, int):
            continue
        eligible_prs.append(number)

    eligible_csv = ",".join(str(n) for n in eligible_prs)
    if len(eligible_prs) < 2:
        _write_output(Path(output_file), {"should_merge": "false", "eligible_csv": eligible_csv})
        return 0

    _write_output(Path(output_file), {"should_merge": "true", "eligible_csv": eligible_csv})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
