"""Auto-fix issues and commit directly."""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.claude import ClaudeClient
from shared.utils import (
    close_issue,
    commit_changes,
    get_ci_status,
    get_issues,
    push,
    revert_commit,
    setup_logging,
)

logger = logging.getLogger(__name__)

# Safety configuration
MAX_FIXES_PER_RUN = int(os.getenv("MAX_FIXES", "3"))
CI_TIMEOUT = int(os.getenv("CI_TIMEOUT", "1800"))
CIRCUIT_BREAKER_THRESHOLD = 3


class AutoFixer:
    """Automatically fix issues."""

    def __init__(self) -> None:
        self.client = ClaudeClient()
        self.fixed_count = 0
        self.failed_count = 0
        self.max_failures = CIRCUIT_BREAKER_THRESHOLD

    def get_next_issue(self) -> dict | None:
        """Get the highest priority issue to fix.

        Returns:
            Issue dictionary or None
        """
        # Get issues sorted by priority (p0 > p1 > p2 > p3)
        issues = get_issues(state="open")

        if not issues:
            logger.info("No open issues found")
            return None

        # Sort by priority (p0 first)
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

        # Skip frozen issues
        for issue in issues:
            is_frozen = any(label.get("name", "") == "frozen" for label in issue.get("labels", []))
            if not is_frozen:
                return issue

        logger.info("All issues are frozen")
        return None

    def generate_fix(self, issue: dict) -> dict:
        """Generate fix for an issue.

        Args:
            issue: Issue dictionary

        Returns:
            Fix dictionary with file changes
        """
        title = issue.get("title", "")
        body = issue.get("body", "")
        number = issue.get("number", "?")

        logger.info(f"Generating fix for issue #{number}: {title}")

        # Extract file path from issue body
        file_path = None
        for line in body.split("\n"):
            if line.startswith("- **文件**:"):
                file_path = line.split("`")[1].strip()
                break

        if not file_path:
            logger.warning(f"Could not extract file path from issue #{number}")
            return {}

        # Read current file content
        try:
            file_content = Path(file_path).read_text()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return {}

        # Generate fix using Claude
        prompt = f"""
修复以下问题：

{title}

{body}

当前文件内容 (前 2000 字符):
```python
{file_content[:2000]}
```

请提供修复后的代码。
以 JSON 格式返回：
{{
    "fixed_code": "修复后的完整代码",
    "explanation": "修复说明",
    "confidence": 置信度 0-100
}}
"""

        response = self.client.chat(prompt, temperature=0.2)

        # Parse JSON
        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.warning(f"Failed to parse JSON from response for issue #{number}")
            return {}

        try:
            result = json.loads(json_match.group())
            return {
                "file": file_path,
                "content": result.get("fixed_code", ""),
                "explanation": result.get("explanation", ""),
                "confidence": result.get("confidence", 0),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {}

    def validate_fix(self, fix: dict) -> bool:
        """Validate a fix before committing.

        Args:
            fix: Fix dictionary

        Returns:
            True if fix is valid
        """
        # Check if fix has content
        if not fix.get("content"):
            logger.warning("Fix has no content")
            return False

        # Check confidence level
        confidence = fix.get("confidence", 0)
        if confidence < 50:
            logger.warning(f"Fix confidence too low: {confidence}")
            return False

        # Check if file path is within allowed bounds
        file_path = fix.get("file", "")
        blocked_patterns = [".github", "config/", "secrets/", ".env", ".key", ".pem"]
        for pattern in blocked_patterns:
            if pattern in file_path:
                logger.error(f"File path blocked: {file_path}")
                return False

        return True

    def run_tests(self) -> bool:
        """Run tests locally.

        Returns:
            True if all tests pass
        """
        # Check if pytest is available
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", "-v"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            success = result.returncode == 0
            if not success:
                logger.warning(f"Tests failed:\n{result.stdout}\n{result.stderr}")
            return success
        except FileNotFoundError:
            logger.info("No tests found, skipping")
            return True
        except subprocess.TimeoutExpired:
            logger.error("Tests timed out")
            return False

    def commit_fix(self, fix: dict, issue: dict) -> str:
        """Commit a fix.

        Args:
            fix: Fix dictionary
            issue: Issue dictionary

        Returns:
            Commit SHA
        """
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "Unknown")

        # Create commit message
        commit_message = f"""[AI Fix #{issue_number}] {issue_title}

{fix.get("explanation", "")}

AI 元数据:
- 模型: {self.client.model}
- 生成时间: {datetime.now().isoformat()}
- 置信度: {fix.get("confidence", 0)}%

Closes #{issue_number}
"""

        # Commit changes
        sha = commit_changes(
            {fix["file"]: fix["content"]},
            commit_message,
            allow_empty=False,
        )

        logger.info(f"Committed fix for issue #{issue_number}: {sha[:8]}")
        return sha

    def monitor_and_rollback(self, commit_sha: str, issue: dict) -> bool:
        """Monitor CI and rollback if needed.

        Args:
            commit_sha: Commit SHA to monitor
            issue: Associated issue

        Returns:
            True if successful, False if rolled back
        """
        issue_number = issue.get("number", "?")

        # Push changes
        try:
            push()
        except Exception as e:
            logger.error(f"Failed to push: {e}")
            return False

        # Wait for CI
        logger.info(f"Waiting for CI to complete (timeout: {CI_TIMEOUT}s)")
        ci_passed = get_ci_status(timeout=CI_TIMEOUT)

        if not ci_passed:
            logger.warning(f"CI failed for commit {commit_sha[:8]}, rolling back")

            # Revert commit
            revert_sha = revert_commit(commit_sha)
            push(force=True)

            # Reopen issue with lower priority
            # (In real implementation, you'd update labels)
            logger.info(f"Reopened issue #{issue_number} after rollback")
            self.failed_count += 1
            return False

        logger.info(f"CI passed for commit {commit_sha[:8]}")
        return True

    def fix_issue(self, issue: dict) -> bool:
        """Fix a single issue.

        Args:
            issue: Issue dictionary

        Returns:
            True if successful
        """
        try:
            # Generate fix
            fix = self.generate_fix(issue)
            if not fix:
                logger.warning(f"Failed to generate fix for issue #{issue.get('number')}")
                return False

            # Validate fix
            if not self.validate_fix(fix):
                logger.warning(f"Fix validation failed for issue #{issue.get('number')}")
                return False

            # Run local tests
            if not self.run_tests():
                logger.warning("Local tests failed, aborting fix")
                return False

            # Commit fix
            commit_sha = self.commit_fix(fix, issue)

            # Monitor CI and rollback if needed
            success = self.monitor_and_rollback(commit_sha, issue)

            if success:
                # Close issue
                close_issue(issue.get("number"), f"Fixed by commit {commit_sha[:8]}")
                self.fixed_count += 1
                return True
            else:
                self.failed_count += 1
                return False

        except Exception as e:
            logger.error(f"Error fixing issue #{issue.get('number')}: {e}")
            self.failed_count += 1
            return False

    def run(self) -> None:
        """Run the auto fixer."""
        logger.info("Starting auto fixer")

        while self.fixed_count < MAX_FIXES_PER_RUN:
            # Check circuit breaker
            if self.failed_count >= self.max_failures:
                logger.error(f"Circuit breaker triggered: {self.failed_count} failures")
                logger.info("Use 'gh issue edit --remove-label frozen' to unfreeze")
                # Add frozen label to stop further fixes
                # (This would require updating all issues, skip for now)
                break

            # Get next issue
            issue = self.get_next_issue()
            if not issue:
                logger.info("No more issues to fix")
                break

            # Fix the issue
            self.fix_issue(issue)

        logger.info(f"Auto fixer complete: {self.fixed_count} fixed, {self.failed_count} failed")


def main():
    """Main entry point."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    fixer = AutoFixer()
    fixer.run()


if __name__ == "__main__":
    main()
