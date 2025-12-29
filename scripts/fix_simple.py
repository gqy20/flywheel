"""Simple auto-fix using claude -p commands."""

import logging
import os
import subprocess

from shared.utils import get_issues, setup_logging

logger = logging.getLogger(__name__)

MAX_FIXES = 3


def get_next_issues(count: int = 3) -> list[dict]:
    """Get next issues to fix."""
    issues = get_issues(state="open")

    # Sort by priority
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
    issues.sort(
        key=lambda x: min(
            [
                priority_order.get(label.get("name", ""), 99)
                for label in x.get("labels", [])
                if label.get("name", "") in priority_order
            ],
            default=99,
        )
    )

    # Filter out frozen/failed
    result = []
    for issue in issues:
        labels = [label.get("name", "") for label in issue.get("labels", [])]
        if "frozen" not in labels and "auto-fix-failed" not in labels:
            result.append(issue)
            if len(result) >= count:
                break

    return result


def fix_issue_with_claude(issue_number: int) -> bool:
    """Fix an issue using claude -p.

    Args:
        issue_number: Issue number to fix

    Returns:
        True if successful
    """
    cmd = ["claude", "-p", f"/fix-issue {issue_number}"]

    logger.info(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minutes
    )

    if result.returncode == 0:
        logger.info(f"Issue #{issue_number} fixed successfully")
        return True
    else:
        logger.error(f"Issue #{issue_number} failed: {result.stderr}")
        # Mark as failed using gh CLI
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--add-label", "auto-fix-failed"],
            capture_output=True,
            check=False,
        )
        return False


def main():
    """Main entry point."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    logger.info("Starting simple claude -p fixer")

    # Get issues to fix
    issues = get_next_issues(MAX_FIXES)

    if not issues:
        logger.info("No issues to fix")
        return

    logger.info(f"Found {len(issues)} issues to fix")

    # Fix each issue
    for issue in issues:
        issue_number = issue.get("number")
        if not isinstance(issue_number, int):
            continue
        logger.info(f"Fixing issue #{issue_number}...")

        if fix_issue_with_claude(issue_number):
            logger.info(f"✅ Issue #{issue_number} fixed")
        else:
            logger.error(f"❌ Issue #{issue_number} failed")

    logger.info("Done!")


if __name__ == "__main__":
    main()
