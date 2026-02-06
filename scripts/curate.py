"""Curate open issues to keep backlog under a configurable cap."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.utils import close_issue, get_issues, setup_logging

logger = logging.getLogger(__name__)


def _priority_rank(labels: list[str]) -> int:
    # Lower rank gets closed first.
    if "p3" in labels:
        return 0
    if "p2" in labels:
        return 1
    if not any(x in labels for x in ("p0", "p1", "p2", "p3")):
        return 2
    if "p1" in labels:
        return 3
    return 4


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.max
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.max


class IssueCurator:
    def __init__(self, max_open_issues: int = 20):
        self.max_open_issues = max_open_issues

    def run(self) -> None:
        issues = get_issues(state="open", limit=200)
        open_count = len(issues)
        logger.info("Open issues before curation: %s", open_count)

        if open_count <= self.max_open_issues:
            logger.info("Within cap (%s). No curation needed.", self.max_open_issues)
            return

        to_close = open_count - self.max_open_issues

        candidates: list[dict] = []
        for issue in issues:
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            if "frozen" in labels:
                continue
            issue["_labels"] = labels
            candidates.append(issue)

        candidates.sort(
            key=lambda x: (
                _priority_rank(x.get("_labels", [])),
                _parse_time(x.get("createdAt")),
                x.get("number", 0),
            )
        )

        selected = candidates[:to_close]
        logger.info("Need to close %s issue(s); selected %s", to_close, len(selected))

        close_comment = (
            "Auto-curation: backlog exceeds policy cap; this issue was closed to keep open volume healthy. "
            "If this is still relevant, comment to request reopen."
        )

        closed_numbers: list[int] = []
        for issue in selected:
            number = issue.get("number")
            if not number:
                continue
            close_issue(number, close_comment)
            closed_numbers.append(number)

        logger.info("Closed issues: %s", closed_numbers)
        logger.info("Open issues after curation target: %s", self.max_open_issues)


def main() -> None:
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))
    max_open_issues = int(os.getenv("MAX_OPEN_ISSUES", "20"))
    curator = IssueCurator(max_open_issues=max_open_issues)
    curator.run()


if __name__ == "__main__":
    main()
