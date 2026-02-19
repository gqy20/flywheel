#!/usr/bin/env python3
"""Close stale duplicate candidate PRs to reduce flywheel backlog."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

TITLE_RE = re.compile(r"^\[AUTOFIX\]\[ISSUE-(?P<issue>\d+)\]\[CANDIDATE-(?P<candidate>\d+)\]")
HEAD_RE = re.compile(r"^claude/issue-(?P<issue>\d+)-candidate-(?P<candidate>\d+)-")


@dataclass(frozen=True)
class CandidatePR:
    number: int
    issue: int
    head_ref: str
    updated_at: datetime
    title: str


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout


def _parse_pr(item: dict) -> CandidatePR | None:
    title = item.get("title", "")
    head_ref = item.get("headRefName", "")
    title_match = TITLE_RE.match(title)
    head_match = HEAD_RE.match(head_ref)
    if not title_match or not head_match:
        return None
    if title_match.group("issue") != head_match.group("issue"):
        return None
    updated_at = datetime.fromisoformat(item["updatedAt"].replace("Z", "+00:00")).astimezone(UTC)
    return CandidatePR(
        number=int(item["number"]),
        issue=int(title_match.group("issue")),
        head_ref=head_ref,
        updated_at=updated_at,
        title=title,
    )


def _list_open_candidate_prs(limit: int) -> list[CandidatePR]:
    out = _run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,headRefName,updatedAt",
        ]
    )
    raw = json.loads(out)
    parsed = [_parse_pr(item) for item in raw]
    return [item for item in parsed if item is not None]


def _select_to_close(
    prs: list[CandidatePR],
    keep_per_issue: int,
    min_age_hours: int,
    close_singleton_after_hours: int | None,
) -> tuple[list[CandidatePR], list[CandidatePR]]:
    grouped: dict[int, list[CandidatePR]] = defaultdict(list)
    for pr in prs:
        grouped[pr.issue].append(pr)

    now = datetime.now(UTC)
    keep: list[CandidatePR] = []
    close: list[CandidatePR] = []
    for issue, items in grouped.items():
        _ = issue
        items_sorted = sorted(items, key=lambda x: x.updated_at, reverse=True)
        if len(items_sorted) <= keep_per_issue:
            for pr in items_sorted:
                age_hours = (now - pr.updated_at).total_seconds() / 3600
                if (
                    close_singleton_after_hours is not None
                    and age_hours >= close_singleton_after_hours
                ):
                    close.append(pr)
                else:
                    keep.append(pr)
            continue
        keep.extend(items_sorted[:keep_per_issue])
        for pr in items_sorted[keep_per_issue:]:
            age_hours = (now - pr.updated_at).total_seconds() / 3600
            if age_hours >= min_age_hours:
                close.append(pr)
            else:
                keep.append(pr)
    return keep, sorted(close, key=lambda x: x.updated_at)


def _close_pr(pr: CandidatePR) -> None:
    body = (
        "Auto hygiene: close stale duplicate candidate PR to reduce queue pressure.\n\n"
        "Policy: keep newest candidate PR(s) per issue and close older duplicates."
    )
    _run(["gh", "pr", "comment", str(pr.number), "--body", body])
    _run(["gh", "pr", "close", str(pr.number)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-per-issue", type=int, default=1)
    parser.add_argument("--min-age-hours", type=int, default=12)
    parser.add_argument("--close-singleton-after-hours", type=int, default=72)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.keep_per_issue < 1:
        raise ValueError("keep-per-issue must be >= 1")
    if args.min_age_hours < 0:
        raise ValueError("min-age-hours must be >= 0")
    if args.close_singleton_after_hours < 0:
        raise ValueError("close-singleton-after-hours must be >= 0")

    prs = _list_open_candidate_prs(limit=args.limit)
    keep, close = _select_to_close(
        prs=prs,
        keep_per_issue=args.keep_per_issue,
        min_age_hours=args.min_age_hours,
        close_singleton_after_hours=args.close_singleton_after_hours,
    )

    print(
        f"open_candidate_prs={len(prs)} keep={len(keep)} close_candidates={len(close)} "
        f"keep_per_issue={args.keep_per_issue} min_age_hours={args.min_age_hours} "
        f"close_singleton_after_hours={args.close_singleton_after_hours} dry_run={args.dry_run}"
    )
    for pr in close:
        print(
            f"close_candidate pr={pr.number} issue={pr.issue} head={pr.head_ref} "
            f"updated_at={pr.updated_at.isoformat()}"
        )

    if args.dry_run:
        return

    for pr in close:
        _close_pr(pr)
        print(f"closed pr={pr.number}")


if __name__ == "__main__":
    main()
