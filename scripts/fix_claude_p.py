"""Auto-fix issues using claude -p CLI tool."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

from shared.utils import get_issues, setup_logging

logger = logging.getLogger(__name__)

# Safety configuration
MAX_FIXES_PER_RUN = int(os.getenv("MAX_FIXES", "3"))
MAX_TOTAL_COMMITS = int(os.getenv("MAX_TOTAL_COMMITS", "15"))
CIRCUIT_BREAKER_THRESHOLD = 3


class ClaudePCliFixer:
    """Auto-fix issues using claude -p CLI tool."""

    def __init__(self) -> None:
        self.fixed_count = 0
        self.failed_count = 0
        self.total_commits = 0
        self.max_failures = CIRCUIT_BREAKER_THRESHOLD

    def get_next_issue(self) -> dict | None:
        """Get the highest priority issue to fix.

        Returns:
            Issue dictionary or None
        """
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

        # Skip frozen and failed issues
        for issue in issues:
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            is_frozen = "frozen" in labels
            is_failed = "auto-fix-failed" in labels
            if not is_frozen and not is_failed:
                return issue

        logger.info("All issues are frozen or failed")
        return None

    def _extract_file_path(self, issue: dict) -> str | None:
        """Extract file path from issue body.

        Args:
            issue: Issue dictionary

        Returns:
            File path or None
        """
        body = issue.get("body", "")
        for line in body.split("\n"):
            if "文件:" in line or "File:" in line:
                try:
                    file_path = cast(str, line.split("`")[1].strip())
                    if "/" in file_path or file_path.endswith(".py"):
                        return file_path
                except (IndexError, AttributeError):
                    continue
        return None

    def _check_commit_limit(self) -> bool:
        """Check if we've reached the commit limit.

        Returns:
            True if under limit, False if limit reached
        """
        if self.total_commits >= MAX_TOTAL_COMMITS:
            logger.warning(f"Commit limit reached: {self.total_commits}/{MAX_TOTAL_COMMITS}")
            return False
        return True

    def _mark_issue_failed(self, issue: dict, reason: str) -> None:
        """Mark an issue as failed to prevent retry loops.

        Args:
            issue: Issue dictionary
            reason: Failure reason
        """
        from shared.utils import update_issue_labels

        issue_number = issue.get("number", "?")
        current_labels = [label.get("name", "") for label in issue.get("labels", [])]

        # Add failure label if not present
        if "auto-fix-failed" not in current_labels:
            new_labels = current_labels + ["auto-fix-failed"]
            try:
                update_issue_labels(issue_number, new_labels)
                logger.info(f"Marked issue #{issue_number} as failed: {reason}")
            except Exception as e:
                logger.error(f"Failed to mark issue #{issue_number}: {e}")

    def _run_claude_p(self, prompt: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        """Run claude -p with the given prompt.

        Args:
            prompt: Prompt to send to claude
            cwd: Working directory

        Returns:
            Completed process result
        """
        cmd = [
            "claude",
            "-p",
            prompt,
        ]

        if cwd:
            cmd.extend(["--cwd", cwd])

        logger.info(f"Running claude -p with prompt: {prompt[:100]}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=600,  # 10 minutes timeout
        )

        return result

    def fix_issue(self, issue: dict) -> bool:
        """Fix a single issue using claude -p.

        Args:
            issue: Issue dictionary

        Returns:
            True if successful
        """
        issue_number = issue.get("number", "?")
        title = issue.get("title", "Unknown")
        body = issue.get("body", "")
        file_path = self._extract_file_path(issue)

        if not file_path:
            logger.warning(f"Could not extract file path from issue #{issue_number}")
            self._mark_issue_failed(issue, "no_file_path")
            return False

        # Check commit limit before starting
        if not self._check_commit_limit():
            logger.info("Commit limit reached, stopping")
            self._mark_issue_failed(issue, "commit_limit")
            return False

        # Build prompt for claude -p
        # The prompt will be processed by the tdd command configuration
        prompt = f"""
请修复以下问题，严格遵循 TDD 工作流：

**Issue #{issue_number}: {title}**

**问题描述**:
{body}

**文件**: {file_path}

**工作流程**（使用 tdd 命令）:
1. 🔴 RED: Read 文件 `{file_path}`，编写失败的测试
2. 运行 `pytest -v` 确认测试失败
3. `git commit -m "test: 添加 {title[:30]} 的失败测试 (#{issue_number})"`
4. 🟢 GREEN: Edit 修改代码使测试通过
5. 运行 `pytest -v` 确认测试通过
6. `git commit -m "feat: 实现 {title[:30]} (#{issue_number})"`
7. 推送到远程

**重要**:
- 使用 Read 工具查看完整文件上下文
- 使用 Edit 工具精确修改代码
- 使用 Bash 工具运行测试和 git 命令
- 每个步骤都要验证成功后再进行下一步
- 如果测试失败，调整代码后重试
- 确保所有测试通过后再提交

请开始修复，按照上述步骤执行。
"""

        logger.info(f"Fixing issue #{issue_number} using claude -p")

        try:
            result = self._run_claude_p(prompt)

            if result.returncode != 0:
                logger.error(f"claude -p failed: {result.stderr}")
                self._mark_issue_failed(issue, "claude_p_failed")
                return False

            # Check if any commits were made
            commit_result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True,
                text=True,
            )

            if commit_result.returncode == 0:
                latest_commit = commit_result.stdout.strip()
                logger.info(f"Latest commit: {latest_commit}")

                # Check if it's our commit (contains issue number)
                if f"#{issue_number}" in latest_commit:
                    logger.info(f"Successfully fixed issue #{issue_number}")
                    self.fixed_count += 1

                    # Count commits (estimate)
                    self.total_commits += 2  # test + fix commits

                    return True

            # If we get here, something went wrong
            logger.warning(f"No commits found for issue #{issue_number}")
            self._mark_issue_failed(issue, "no_commits")
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"claude -p timed out for issue #{issue_number}")
            self._mark_issue_failed(issue, "timeout")
            return False
        except Exception as e:
            logger.error(f"Error fixing issue #{issue_number}: {e}")
            self._mark_issue_failed(issue, f"exception: {str(e)[:100]}")
            return False

    def collect_issues_to_fix(self, count: int) -> list[dict]:
        """Collect issues to fix in batch.

        Args:
            count: Number of issues to collect

        Returns:
            List of issues to fix
        """
        issues = get_issues(state="open")

        if not issues:
            return []

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

        # Filter and collect
        result = []
        for issue in issues:
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            is_frozen = "frozen" in labels
            is_failed = "auto-fix-failed" in labels
            if not is_frozen and not is_failed:
                result.append(issue)
                if len(result) >= count:
                    break

        return result

    def generate_fix_commands(self, issues: list[dict]) -> list[str]:
        """Generate claude -p commands for each issue.

        Args:
            issues: List of issues to fix

        Returns:
            List of command strings (prompts with /tdd prefix)
        """
        prompts = []

        for issue in issues:
            issue_number = issue.get("number", "?")
            title = issue.get("title", "Unknown")
            body = issue.get("body", "")
            file_path = self._extract_file_path(issue)

            if not file_path:
                logger.warning(f"Skipping issue #{issue_number}: no file path")
                continue

            # Generate prompt with /tdd prefix
            # The /tdd command loads .claude/commands/tdd.md context
            prompt = f"""/tdd

请修复以下 Issue #{issue_number}: {title}

**问题描述**:
{body}

**目标文件**: {file_path}

请按照 TDD 工作流执行：
1. 🔴 RED: Read `{file_path}` 了解代码，编写失败测试
2. 运行 pytest 验证测试失败
3. git commit 提交测试
4. 🟢 GREEN: Edit 修改代码使测试通过
5. 运行 pytest 验证测试通过
6. git commit 提交修复

请开始。"""
            prompts.append(prompt)

        return prompts

    def run_batch(self, count: int = 3) -> None:
        """Run claude -p fixer in batch mode.

        Args:
            count: Number of issues to fix in this batch
        """
        logger.info(f"Starting batch claude -p fixer (batch size: {count})")

        # Collect issues
        issues = self.collect_issues_to_fix(count)

        if not issues:
            logger.info("No issues to fix")
            return

        logger.info(f"Collected {len(issues)} issues to fix")

        # Generate commands
        prompts = self.generate_fix_commands(issues)

        # Execute each prompt
        for i, prompt in enumerate(prompts, 1):
            logger.info(f"Processing issue {i}/{len(prompts)}")

            result = self._run_claude_p(prompt)

            if result.returncode == 0:
                logger.info(f"Issue {i} fixed successfully")
                self.fixed_count += 1
            else:
                logger.error(f"Issue {i} failed: {result.stderr}")
                self.failed_count += 1

        logger.info(f"Batch complete: {self.fixed_count} fixed, {self.failed_count} failed")

    def run(self) -> None:
        """Run the auto fixer."""
        logger.info(
            f"Starting claude -p fixer (max commits: {MAX_TOTAL_COMMITS}, max fixes: {MAX_FIXES_PER_RUN})"
        )

        # Process in batches
        batch_size = min(MAX_FIXES_PER_RUN, 3)
        self.run_batch(batch_size)

        logger.info(
            f"Claude -p fixer complete: {self.fixed_count} fixed, {self.failed_count} failed"
        )


def main():
    """Main entry point."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    fixer = ClaudePCliFixer()
    fixer.run()
