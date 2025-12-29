"""Utility functions and helpers."""

import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_gh_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run gh CLI command.

    Args:
        args: Command arguments
        check: Whether to raise on non-zero exit

    Returns:
        Completed process result
    """
    cmd = ["gh"] + args

    # Set GITHUB_TOKEN from environment if not set
    env = os.environ.copy()
    if "GITHUB_TOKEN" not in env:
        # gh CLI automatically uses GH_TOKEN or GITHUB_TOKEN
        pass

    logger.debug(f"Running: {' '.join(cmd)}")

    return subprocess.run(cmd, check=check, capture_output=True, text=True, env=env)


def create_issue(title: str, body: str, labels: list[str]) -> int:
    """Create a GitHub issue.

    Args:
        title: Issue title
        body: Issue body
        labels: List of labels

    Returns:
        Issue number
    """
    cmd = [
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--label",
        ",".join(labels),
    ]

    result = run_gh_command(cmd)
    # Output format: "https://github.com/owner/repo/issues/123"
    url = result.stdout.strip()
    issue_number = int(url.split("/")[-1])
    logger.info(f"Created issue #{issue_number}: {title}")
    return issue_number


def get_issues(
    labels: list[str] | None = None,
    state: str = "open",
    limit: int = 100,
) -> list[dict]:
    """Get list of issues.

    Args:
        labels: Filter by labels
        state: open or closed
        limit: Max results

    Returns:
        List of issue dictionaries
    """
    cmd = [
        "issue",
        "list",
        "--json",
        "number,title,labels,body,state",
        "--limit",
        str(limit),
        "--state",
        state,
    ]

    if labels:
        cmd.extend(["--label", ",".join(labels)])

    result = run_gh_command(cmd)
    return json.loads(result.stdout)


def update_issue_labels(issue_number: int, labels: list[str]) -> None:
    """Update issue labels (replaces all existing labels).

    Args:
        issue_number: Issue number
        labels: List of labels to set (replaces all current labels)
    """
    # Use GitHub API to replace all labels
    # gh CLI :owner/:repo placeholders are auto-resolved
    cmd = [
        "api",
        "--method",
        "PATCH",
        f"repos/:owner/:repo/issues/{issue_number}",
        "-f",
        f"labels={json.dumps(labels)}",
    ]

    run_gh_command(cmd)
    logger.info(f"Updated issue #{issue_number} labels: {labels}")


def close_issue(issue_number: int, comment: str | None = None) -> None:
    """Close an issue.

    Args:
        issue_number: Issue number
        comment: Optional closing comment
    """
    cmd = ["issue", "close", str(issue_number)]

    if comment:
        cmd.extend(["--comment", comment])

    run_gh_command(cmd)
    logger.info(f"Closed issue #{issue_number}")


def reopen_issue(issue_number: int, comment: str | None = None) -> None:
    """Reopen a closed issue.

    Args:
        issue_number: Issue number
        comment: Optional comment explaining the reopen
    """
    cmd = ["issue", "reopen", str(issue_number)]

    run_gh_command(cmd)

    if comment:
        comment_issue(issue_number, comment)

    logger.info(f"Reopened issue #{issue_number}")


def comment_issue(issue_number: int, comment: str) -> None:
    """Add a comment to an issue.

    Args:
        issue_number: Issue number
        comment: Comment body
    """
    run_gh_command(
        [
            "issue",
            "comment",
            str(issue_number),
            "--body",
            comment,
        ]
    )
    logger.info(f"Commented on issue #{issue_number}")


def get_file_content(filepath: str) -> str:
    """Get file content from repository.

    Args:
        filepath: Path to file

    Returns:
        File content
    """
    result = run_gh_command(["view", filepath])
    return result.stdout


def commit_changes(
    files: dict[str, str],
    message: str,
    branch: str | None = None,
    allow_empty: bool = False,
) -> str:
    """Commit changes to repository.

    Args:
        files: Dictionary of filepath -> content
        message: Commit message
        branch: Optional branch name (defaults to current)
        allow_empty: Allow empty commits

    Returns:
        Commit SHA
    """
    # Write files
    for filepath, content in files.items():
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(content)

    # Stage files
    subprocess.run(["git", "add"] + list(files.keys()), check=True)

    # Commit
    cmd = ["commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")

    subprocess.run(["git"] + cmd, check=True)

    # Get commit SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    sha = result.stdout.strip()

    logger.info(f"Committed {len(files)} files: {sha[:8]}")
    return sha


def push(branch: str | None = None, force: bool = False) -> None:
    """Push changes to remote.

    Args:
        branch: Branch name (defaults to current)
        force: Force push
    """
    cmd = ["push"]
    if branch:
        cmd.extend(["origin", branch])
    else:
        cmd.append("origin")

    if force:
        cmd.append("--force")

    subprocess.run(["git"] + cmd, check=True)
    logger.info("Pushed to remote")


def create_branch(name: str, base: str = "main") -> None:
    """Create a new branch.

    Args:
        name: Branch name
        base: Base branch
    """
    subprocess.run(["git", "checkout", "-b", name, f"origin/{base}"], check=True)
    logger.info(f"Created branch: {name}")


def merge_branch(branch: str, method: str = "merge") -> None:
    """Merge a branch.

    Args:
        branch: Branch to merge
        method: merge, squash, or rebase
    """
    if method == "merge":
        subprocess.run(["git", "merge", branch, "--no-ff"], check=True)
    elif method == "squash":
        subprocess.run(["git", "merge", "--squash", branch], check=False)
        subprocess.run(["git", "commit", "--no-edit"], check=False)
    else:
        subprocess.run(["git", "rebase", branch], check=False)

    logger.info(f"Merged branch: {branch}")


def revert_commit(sha: str) -> str:
    """Revert a commit.

    Args:
        sha: Commit SHA to revert

    Returns:
        New commit SHA
    """
    subprocess.run(["git", "revert", "--no-edit", sha], check=True)

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    new_sha = result.stdout.strip()

    logger.info(f"Reverted commit {sha[:8]} -> {new_sha[:8]}")
    return new_sha


def get_ci_status(timeout: int = 1800) -> bool:
    """Wait for CI to complete and return status.

    Args:
        timeout: Timeout in seconds

    Returns:
        True if CI passed, False otherwise
    """
    # This is a placeholder - actual implementation depends on CI system
    # For GitHub Actions, you'd use the GitHub API to check workflow runs
    import time

    start = time.time()
    while time.time() - start < timeout:
        # Check CI status (simplified)
        result = subprocess.run(
            ["gh", "run", "list", "--json", "conclusion", "--limit", "1"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            runs = json.loads(result.stdout)
            if runs:
                status = runs[0].get("conclusion")
                if status == "success":
                    return True
                elif status in ("failure", "cancelled"):
                    return False

        time.sleep(30)  # Check every 30 seconds

    logger.warning("CI status check timed out")
    return False


def setup_logging(level: str = "INFO") -> None:
    """Setup logging.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
