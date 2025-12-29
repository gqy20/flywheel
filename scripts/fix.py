"""Auto-fix issues and commit directly."""

import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent))

from shared.claude import ClaudeClient
from shared.utils import (
    close_issue,
    commit_changes,
    get_ci_status,
    get_issues,
    push,
    reopen_issue,
    revert_commit,
    setup_logging,
    update_issue_labels,
)

logger = logging.getLogger(__name__)

# Safety configuration
MAX_FIXES_PER_RUN = int(os.getenv("MAX_FIXES", "3"))
CI_TIMEOUT = int(os.getenv("CI_TIMEOUT", "1800"))
CIRCUIT_BREAKER_THRESHOLD = 3


def get_commit_type(issue_title: str) -> str:
    """Determine commit type from issue title.

    Args:
        issue_title: Issue title

    Returns:
        Commit type (conventional commits)
    """
    title_lower = issue_title.lower()

    # Check for type prefixes
    if any(keyword in title_lower for keyword in ["bug", "修复", "fix", "错误"]):
        return "fix"
    if any(keyword in title_lower for keyword in ["test", "测试", "覆盖"]):
        return "test"
    if any(keyword in title_lower for keyword in ["refactor", "重构", "优化"]):
        return "refactor"
    if any(keyword in title_lower for keyword in ["doc", "文档", "readme"]):
        return "docs"
    if any(keyword in title_lower for keyword in ["chore", "杂项", "配置"]):
        return "chore"
    if any(keyword in title_lower for keyword in ["feat", "功能", "新增", "添加"]):
        return "feat"
    if any(keyword in title_lower for keyword in ["perf", "性能"]):
        return "perf"

    # Default to chore for maintenance
    return "chore"


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

    def _extract_file_path(self, issue: dict) -> str | None:
        """Extract file path from issue body.

        Args:
            issue: Issue dictionary

        Returns:
            File path or None
        """
        body = issue.get("body", "")
        for line in body.split("\n"):
            # Support multiple formats:
            # - - **文件**:`path` (with bold)
            # - - 文件:`path` (without bold, current scan format)
            # - - **File**:`path` (English)
            if "文件:" in line or "File:" in line:
                try:
                    # Extract content between backticks
                    file_path = cast(str, line.split("`")[1].strip())
                    # Validate it looks like a file path
                    if "/" in file_path or file_path.endswith(".py"):
                        return file_path
                except (IndexError, AttributeError):
                    continue
        return None

    def _read_file_content(self, file_path: str) -> str:
        """Read file content.

        Args:
            file_path: Path to file

        Returns:
            File content
        """
        try:
            return Path(file_path).read_text()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return ""

    def _parse_json_response(self, response: str, context: str) -> dict | None:
        """Parse JSON response from Claude.

        Args:
            response: Claude response text
            context: Context for error messages

        Returns:
            Parsed dict or None
        """
        import json

        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.warning(f"Failed to parse JSON from response: {context}")
            return None

        try:
            return cast(dict[str, Any], json.loads(json_match.group()))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None

    def generate_test(self, issue: dict) -> dict | None:
        """🔴 RED: Generate failing test for the issue.

        Args:
            issue: Issue dictionary

        Returns:
            Test dictionary with test code
        """
        title = issue.get("title", "")
        body = issue.get("body", "")
        number = issue.get("number", "?")
        file_path = self._extract_file_path(issue)

        if not file_path:
            logger.warning(f"Could not extract file path from issue #{number}")
            return None

        logger.info(f"🔴 RED: Generating test for issue #{number}: {title}")

        file_content = self._read_file_content(file_path)
        if not file_content:
            return None

        # Extract function/class name from file path
        module_name = Path(file_path).stem

        # Generate test using Claude
        prompt = f"""为以下问题编写单元测试（测试驱动开发第一步）：

问题描述：
{title}

详情：
{body}

当前代码：
```python
{file_content[:3000]}
```

请编写一个 pytest 测试用例，验证修复后的功能正常工作。

要求：
1. 使用 AAA 模式（Arrange-Act-Assert）
2. 测试命名：test_功能_条件_期望
3. 包含正常情况和边界情况
4. 测试应该在当前代码下失败（因为问题还没修复）

以 JSON 格式返回：
{{
    "test_file": "tests/test_{module_name}.py",
    "test_code": "完整的测试代码",
    "description": "测试说明"
}}
"""

        response = self.client.chat(prompt, temperature=0.2)
        result = self._parse_json_response(response, f"issue #{number}")

        if result:
            return {
                "file": result.get("test_file", f"tests/test_{module_name}.py"),
                "content": result.get("test_code", ""),
                "description": result.get("description", ""),
            }
        return None

    def generate_fix(self, issue: dict) -> dict | None:
        """🟢 GREEN: Generate fix code that makes tests pass.

        Args:
            issue: Issue dictionary

        Returns:
            Fix dictionary with fixed code
        """
        title = issue.get("title", "")
        body = issue.get("body", "")
        number = issue.get("number", "?")
        file_path = self._extract_file_path(issue)

        if not file_path:
            logger.warning(f"Could not extract file path from issue #{number}")
            return None

        logger.info(f"🟢 GREEN: Generating fix for issue #{number}: {title}")

        file_content = self._read_file_content(file_path)
        if not file_content:
            return None

        # Generate fix using Claude
        prompt = f"""修复以下问题（测试驱动开发第二步）：

问题描述：
{title}

详情：
{body}

当前代码：
```python
{file_content[:3000]}
```

请提供修复后的代码，确保相关测试能够通过。

以 JSON 格式返回：
{{
    "fixed_code": "修复后的完整代码",
    "explanation": "修复说明",
    "confidence": 置信度 0-100
}}
"""

        response = self.client.chat(prompt, temperature=0.2)
        result = self._parse_json_response(response, f"issue #{number}")

        if result:
            return {
                "file": file_path,
                "content": result.get("fixed_code", ""),
                "explanation": result.get("explanation", ""),
                "confidence": result.get("confidence", 0),
            }
        return None

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

    def commit_test(self, test: dict, issue: dict) -> str:
        """Commit a test using conventional commit format (TDD RED phase).

        Args:
            test: Test dictionary
            issue: Issue dictionary

        Returns:
            Commit SHA
        """
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "Unknown")

        # Create short description
        short_desc = issue_title[:40]
        if len(issue_title) > 40:
            short_desc = issue_title[:37] + "..."

        # TDD RED phase always uses "test:" prefix
        commit_message = f"""test: 添加 {short_desc} 的失败测试 (#{issue_number})

{test.get("description", "")}

🔴 RED - TDD Phase 1: 先写一个失败的测试

Issue: {issue_title}
Test file: {test.get("file")}

---
AI-generated test by AI Flywheel
Model: {self.client.model}
Generated: {datetime.now().isoformat()}
Closes #{issue_number}
"""

        # Commit test file
        sha = commit_changes(
            {test["file"]: test["content"]},
            commit_message,
            allow_empty=False,
        )

        logger.info(f"🔴 RED: Committed test for issue #{issue_number}: {sha[:8]}")
        return sha

    def commit_fix(self, fix: dict, issue: dict) -> str:
        """Commit a fix using conventional commit format (TDD GREEN phase).

        Args:
            fix: Fix dictionary
            issue: Issue dictionary

        Returns:
            Commit SHA
        """
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "Unknown")

        # Get commit type from issue title
        commit_type = get_commit_type(issue_title)

        # Create short description (max 50 chars for conventional commits)
        short_desc = issue_title[:50]
        if len(issue_title) > 50:
            short_desc = issue_title[:47] + "..."

        # Create commit message in conventional commit format
        commit_message = f"""{commit_type}: {short_desc} (#{issue_number})

{fix.get("explanation", "")}

🟢 GREEN - TDD Phase 2: 实现使测试通过的功能

Issue: {issue_title}

---
AI-generated fix by AI Flywheel
Model: {self.client.model}
Confidence: {fix.get("confidence", 0)}%
Generated: {datetime.now().isoformat()}
Closes #{issue_number}
"""

        # Commit changes using git
        sha = commit_changes(
            {fix["file"]: fix["content"]},
            commit_message,
            allow_empty=False,
        )

        logger.info(f"🟢 GREEN: Committed fix for issue #{issue_number}: {sha[:8]}")
        logger.info(f"Commit type: {commit_type}, message: {commit_type}: {short_desc}")
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

            # Reopen issue with detailed comment
            rollback_comment = f"""## ⚠️ CI 失败 - 修复已回滚

**回滚信息**
- 失败提交: `{commit_sha[:8]}`
- 回滚提交: `{revert_sha[:8]}`
- 回滚时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**下一步**
- Issue 已重新开放，需要人工检查
- 优先级已降低，等待进一步处理

---
*AI Flywheel 自动回滚 • 失败计数: {self.failed_count + 1}/{self.max_failures}*
"""
            reopen_issue(issue_number, rollback_comment)

            # Downgrade priority (p0→p1, p1→p2, p2→p3)
            current_priority = issue.get("priority", "p2")
            priorities = ["p0", "p1", "p2", "p3"]
            try:
                current_idx = priorities.index(current_priority)
                if current_idx < len(priorities) - 1:
                    new_priority = priorities[current_idx + 1]
                    update_issue_labels(issue_number, [new_priority])
                    logger.info(f"Downgraded priority: {current_priority} → {new_priority}")
            except ValueError:
                pass  # Priority not in list, skip

            self.failed_count += 1
            return False

        logger.info(f"CI passed for commit {commit_sha[:8]}")
        return True

    def should_update_readme(self, fix: dict, issue: dict) -> bool:
        """Check if README needs update after this fix.

        Args:
            fix: Fix dictionary
            issue: Issue dictionary

        Returns:
            True if README should be updated
        """
        issue_title = issue.get("title", "").lower()
        file_path = fix.get("file", "")

        # Check if it's a feature addition to CLI
        is_cli_feature = any(
            kw in issue_title for kw in ["feat", "功能", "新增", "添加", "add", "feature"]
        )
        is_cli_file = "cli.py" in file_path or "formatter.py" in file_path

        # Skip for internal fixes, refactor, docs
        is_internal = any(
            kw in issue_title for kw in ["refactor", "重构", "test", "测试", "fix", "修复"]
        )
        is_docs = "docs" in file_path or "readme" in file_path.lower()

        return (is_cli_feature and is_cli_file) and not (is_internal or is_docs)

    def update_readme(self, fix: dict, issue: dict) -> str | None:
        """Update README.md after feature addition.

        Args:
            fix: Fix dictionary
            issue: Issue dictionary

        Returns:
            Commit SHA or None
        """
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "Unknown")

        readme_path = Path("README.md")
        if not readme_path.exists():
            logger.warning("README.md not found")
            return None

        # Read current README
        current_readme = readme_path.read_text()

        # Generate README update using Claude
        prompt = f"""
根据以下代码修复，更新 README.md 中的使用示例部分。

问题描述：{issue_title}
详情：{issue.get("body", "")}

修改的文件：{fix.get("file")}

当前 README 内容：
```markdown
{current_readme[:3000]}
```

请提供更新后的完整 README.md 内容：

1. 在"## 功能"部分添加新功能的简要说明
2. 在"## 快速开始"部分的"使用 Todo CLI"中添加使用示例
3. 保持其他内容不变
4. 使用现有的格式风格

以 JSON 格式返回：
{{
    "readme_content": "更新后的完整 README.md 内容",
    "changes": ["添加了 xxx 功能的使用示例"]
}}
"""

        response = self.client.chat(prompt, temperature=0.2)
        result = self._parse_json_response(response, f"README update for issue #{issue_number}")

        if not result or not result.get("readme_content"):
            logger.warning(f"Failed to generate README update for issue #{issue_number}")
            return None

        # Create commit message
        short_desc = issue_title[:40]
        if len(issue_title) > 40:
            short_desc = issue_title[:37] + "..."

        commit_message = f"""docs: 更新 README 使用示例 ({short_desc}) (#{issue_number})

{chr(10).join(result.get("changes", []))}

📚 文档同步 - 新功能使用说明

Issue: {issue_title}

---
AI-generated documentation by AI Flywheel
Model: {self.client.model}
Generated: {datetime.now().isoformat()}
Related to: #{issue_number}
"""

        # Commit README update
        sha = commit_changes(
            {"README.md": result["readme_content"]},
            commit_message,
            allow_empty=False,
        )

        logger.info(f"📚 README updated: {sha[:8]}")
        return sha

    def fix_issue(self, issue: dict) -> bool:
        """Fix a single issue using TDD workflow.

        TDD Cycle:
        1. 🔴 RED: Write failing test
        2. 🟢 GREEN: Write minimal code to pass
        3. 📚 DOCS: Update README (if feature addition)
        4. Monitor CI and rollback if needed

        Args:
            issue: Issue dictionary

        Returns:
            True if successful
        """
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "Unknown")

        try:
            # 🔴 RED Phase: Generate and commit failing test
            logger.info(f"🔴 RED Phase: Generating test for issue #{issue_number}")
            test = self.generate_test(issue)

            if not test:
                logger.warning(f"Failed to generate test for issue #{issue_number}")
                return False

            # Commit the failing test
            test_commit = self.commit_test(test, issue)
            logger.info(f"Test committed: {test_commit[:8]}")

            # 🟢 GREEN Phase: Generate fix
            logger.info(f"🟢 GREEN Phase: Generating fix for issue #{issue_number}")
            fix = self.generate_fix(issue)

            if not fix:
                logger.warning(f"Failed to generate fix for issue #{issue_number}")
                return False

            # Validate fix
            if not self.validate_fix(fix):
                logger.warning(f"Fix validation failed for issue #{issue_number}")
                return False

            # Commit the fix
            fix_commit = self.commit_fix(fix, issue)
            logger.info(f"Fix committed: {fix_commit[:8]}")

            # Run local tests to verify
            if not self.run_tests():
                logger.warning("Local tests failed, aborting fix")
                # Rollback the fix commit
                revert_commit(fix_commit)
                push(force=True)
                return False

            # Monitor CI and rollback if needed
            success = self.monitor_and_rollback(fix_commit, issue)

            if not success:
                self.failed_count += 1
                return False

            # 📚 DOCS Phase: Update README if this is a feature addition
            if self.should_update_readme(fix, issue):
                logger.info(f"📚 DOCS Phase: Updating README for issue #{issue_number}")
                readme_commit = self.update_readme(fix, issue)
                if readme_commit:
                    logger.info(f"README updated: {readme_commit[:8]}")
                    # Push README update
                    try:
                        push()
                    except Exception as e:
                        logger.warning(f"Failed to push README update: {e}")
                else:
                    logger.info(f"README update skipped for issue #{issue_number}")

            # Close issue with detailed comment
            closing_comment = f"""## ✅ 修复完成

**修复信息**
- 提交: `{fix_commit[:8]}`
- 完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}

**修复说明**
{fix.get("explanation", "见提交详情")}

---
*AI Flywheel 自动修复 • {self.client.model} • 置信度: {fix.get("confidence", 0)}%*
"""
            close_issue(issue_number, closing_comment)
            self.fixed_count += 1
            return True

        except Exception as e:
            logger.error(f"Error fixing issue #{issue_number}: {e}")
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
