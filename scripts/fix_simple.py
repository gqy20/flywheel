"""Simple auto-fix using claude -p commands."""

import logging
import os
import subprocess
from pathlib import Path

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
    # Read the command file and replace $1 with issue number
    cmd_file = Path(__file__).parent.parent / ".claude" / "commands" / "fix-issue.md"
    prompt = cmd_file.read_text().replace("$1", str(issue_number))

    cmd = [
        "claude",
        "-p",
        "-",
        "--allowed-tools",
        "Bash(git:*),Bash(pytest),Bash(gh:*),Read,Edit,Write",
    ]

    logger.info(f"Running: claude -p with fix-issue.md for #{issue_number}")

    # Prepare environment with API key
    env = os.environ.copy()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minutes
        env=env,
    )

    # Log output for debugging
    logger.info(f"stdout: {result.stdout[:1000]}")
    if result.stderr:
        logger.warning(f"stderr: {result.stderr[:500]}")

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
