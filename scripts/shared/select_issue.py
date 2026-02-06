"""Select the best issue candidate for autofix in GitHub Actions."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXCLUDED_LABELS = {
    "frozen",
    "auto-fix-failed",
    "wontfix",
    "invalid",
    "question",
    "duplicate",
}
PRIORITY_RANK = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}


@dataclass(frozen=True)
class IssueCandidate:
    number: int
    title: str
    url: str
    labels: set[str]
    priority: int


def _api_get(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "flywheel-select-issue",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API error: HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API unreachable: {exc.reason}") from exc


def _list_open_pr_titles(repo: str, token: str, limit: int = 200) -> list[str]:
    owner = repo.split("/", 1)[0]
    titles: list[str] = []
    per_page = 100
    for page in range(1, 1 + (limit + per_page - 1) // per_page):
        url = (
            f"https://api.github.com/repos/{repo}/pulls?state=open&per_page={per_page}&page={page}"
        )
        batch = _api_get(url, token)
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            title = item.get("title")
            if isinstance(title, str):
                titles.append(title)
        if len(batch) < per_page or len(titles) >= limit:
            break
    return titles[:limit]


def _busy_issue_numbers_from_titles(titles: list[str]) -> set[int]:
    busy: set[int] = set()
    prefix = "[AUTOFIX][ISSUE-"
    for title in titles:
        if not title.startswith(prefix):
            continue
        suffix = title[len(prefix) :]
        issue_part = suffix.split("]", 1)[0]
        if issue_part.isdigit():
            busy.add(int(issue_part))
    return busy


def _list_open_issues(repo: str, token: str, limit: int = 100) -> list[IssueCandidate]:
    result: list[IssueCandidate] = []
    per_page = 100
    for page in range(1, 1 + (limit + per_page - 1) // per_page):
        url = (
            f"https://api.github.com/repos/{repo}/issues?state=open&per_page={per_page}&page={page}"
        )
        batch = _api_get(url, token)
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            if "pull_request" in item:
                continue
            number = item.get("number")
            title = item.get("title")
            url = item.get("html_url")
            labels_raw = item.get("labels", [])
            if (
                not isinstance(number, int)
                or not isinstance(title, str)
                or not isinstance(url, str)
            ):
                continue
            labels: set[str] = set()
            if isinstance(labels_raw, list):
                for label in labels_raw:
                    if isinstance(label, dict):
                        name = label.get("name")
                        if isinstance(name, str):
                            labels.add(name)
            priority = min((PRIORITY_RANK.get(label, 99) for label in labels), default=99)
            result.append(
                IssueCandidate(
                    number=number,
                    title=title,
                    url=url,
                    labels=labels,
                    priority=priority,
                )
            )
        if len(batch) < per_page or len(result) >= limit:
            break
    return result[:limit]


def _select_best_issue(issues: list[IssueCandidate], busy: set[int]) -> list[IssueCandidate]:
    eligible: list[IssueCandidate] = []
    for issue in issues:
        if issue.number in busy:
            continue
        if issue.labels & EXCLUDED_LABELS:
            continue
        eligible.append(issue)
    eligible.sort(key=lambda i: (i.priority, i.number))
    return eligible


def _write_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")


def main() -> int:
    repo = os.getenv("GH_REPO", os.getenv("GITHUB_REPOSITORY", ""))
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    output_file = os.getenv("GITHUB_OUTPUT", "")
    min_fixable_issues = int(os.getenv("MIN_FIXABLE_ISSUES", "3"))
    issue_batch_size = max(1, int(os.getenv("ISSUE_BATCH_SIZE", "1")))

    if not repo or not token or not output_file:
        print("missing GH_REPO/GH_TOKEN/GITHUB_OUTPUT", file=sys.stderr)
        return 2

    open_pr_titles = _list_open_pr_titles(repo, token, limit=200)
    busy_issue_numbers = _busy_issue_numbers_from_titles(open_pr_titles)
    issues = _list_open_issues(repo, token, limit=100)
    eligible = _select_best_issue(issues, busy_issue_numbers)

    if len(eligible) < min_fixable_issues:
        print(
            f"Fixable issue pool too small: eligible={len(eligible)}, required={min_fixable_issues}"
        )
        _write_output(
            Path(output_file),
            {"should_run": "false", "issues_json": "[]", "selected_count": "0"},
        )
        return 0

    if not eligible:
        print("No eligible issue found.")
        _write_output(
            Path(output_file),
            {"should_run": "false", "issues_json": "[]", "selected_count": "0"},
        )
        return 0

    selected = eligible[:issue_batch_size]
    best = selected[0]
    issues_json = json.dumps(
        [
            {
                "number": str(item.number),
                "title": item.title,
                "url": item.url,
            }
            for item in selected
        ],
        ensure_ascii=True,
    )

    _write_output(
        Path(output_file),
        {
            "should_run": "true",
            "issue_number": str(best.number),
            "issue_title": best.title,
            "issue_url": best.url,
            "issues_json": issues_json,
            "selected_count": str(len(selected)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
