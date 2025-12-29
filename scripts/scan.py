"""Scan code and create issues."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from shared.claude import ClaudeClient
from shared.utils import create_issue, get_issues, setup_logging

logger = logging.getLogger(__name__)

# 类型到优先级的初步映射
TYPE_TO_PRIORITY = {
    "Security": "p0",
    "Bug": "p1",
    "Perf": "p1",
    "Test": "p2",
    "Refactor": "p2",
    "Docs": "p3",
}


class Scanner:
    """Code scanner that finds issues using Claude."""

    def __init__(self) -> None:
        self.client = ClaudeClient()
        self.max_issues = int(os.getenv("MAX_ISSUES", "5"))
        self.created = 0

    def scan_file(self, filepath: str) -> list[dict]:
        """Scan a single file for issues.

        Args:
            filepath: Path to file

        Returns:
            List of found issues
        """
        try:
            content = Path(filepath).read_text()
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            return []

        logger.info(f"Scanning {filepath} ({len(content)} chars)")

        issues = self.client.analyze_code(content, filepath)
        logger.info(f"Found {len(issues)} issues in {filepath}")

        # Add filepath to each issue
        for issue in issues:
            issue["file"] = filepath

        return issues

    def scan_directory(self, directory: str, patterns: list[str] | None = None) -> list[dict]:
        """Scan directory for issues.

        Args:
            directory: Directory to scan
            patterns: File patterns to include (default: *.py)

        Returns:
            List of all found issues
        """
        if patterns is None:
            patterns = ["*.py"]

        all_issues = []
        base_path = Path(directory)

        for pattern in patterns:
            for filepath in base_path.rglob(pattern):
                if self.created >= self.max_issues:
                    logger.info(f"Reached max issues limit: {self.max_issues}")
                    return all_issues

                issues = self.scan_file(str(filepath))
                all_issues.extend(issues)

        return all_issues

    def deduplicate_issues(self, issues: list[dict]) -> list[dict]:
        """Remove duplicate issues.

        Args:
            issues: List of issues

        Returns:
            Deduplicated issues
        """
        seen = set()
        unique_issues = []

        for issue in issues:
            # Create a unique key based on type + description + location
            key = (
                issue.get("type", ""),
                issue.get("description", "")[:100],
                issue.get("file", ""),
                issue.get("line", ""),
            )

            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return unique_issues

    def filter_existing_issues(self, issues: list[dict]) -> list[dict]:
        """Filter out issues that already exist.

        Args:
            issues: List of new issues

        Returns:
            Filtered issues
        """
        existing_issues = get_issues(state="open")
        existing_titles = {issue["title"] for issue in existing_issues}

        new_issues = []
        for issue in issues:
            title = f"[{issue['type']}] {issue['description'][:80]}"
            if title not in existing_titles:
                new_issues.append(issue)
            else:
                logger.debug(f"Issue already exists: {title}")

        logger.info(f"Filtered {len(issues) - len(new_issues)} duplicate issues")
        return new_issues

    def get_priority_for_type(self, issue_type: str) -> str:
        """Get initial priority for issue type.

        Args:
            issue_type: Issue type (Security, Bug, etc.)

        Returns:
            Priority label
        """
        return TYPE_TO_PRIORITY.get(issue_type, "p2")

    def ensure_diverse_distribution(self, issues: list[dict]) -> list[dict]:
        """Ensure issues are distributed across different types.

        Args:
            issues: List of issues

        Returns:
            Balanced list of issues (max max_issues)
        """
        if not issues:
            return []

        # Group by priority
        by_priority = defaultdict(list)
        for issue in issues:
            priority = self.get_priority_for_type(issue.get("type", ""))
            by_priority[priority].append(issue)

        # Select issues ensuring diversity (at most 1-2 per priority level)
        selected = []
        max_per_priority = 2  # Each priority level at most 2 issues

        # Prioritize order: p0 > p1 > p2 > p3
        for priority in ["p0", "p1", "p2", "p3"]:
            issues_of_priority = by_priority.get(priority, [])
            for issue in issues_of_priority[:max_per_priority]:
                if len(selected) < self.max_issues:
                    issue["severity"] = priority
                    selected.append(issue)

        # If we still need more, fill from remaining
        if len(selected) < self.max_issues:
            for priority in ["p1", "p2", "p3"]:  # p0 is rare
                issues_of_priority = by_priority.get(priority, [])
                for issue in issues_of_priority[max_per_priority:]:
                    if len(selected) < self.max_issues:
                        issue["severity"] = priority
                        selected.append(issue)

        # Log distribution
        dist = defaultdict(int)
        for issue in selected:
            dist[issue.get("severity", "p2")] += 1
        logger.info(f"Issue distribution: {dict(dist)}")

        return selected

    def create_issue_from_data(self, issue: dict) -> int:
        """Create a GitHub issue from issue data.

        Args:
            issue: Issue dictionary

        Returns:
            Issue number
        """
        title = f"[{issue['type']}] {issue['description'][:80]}"
        priority = issue.get("severity", "p2")

        body = f"""## 问题描述
{issue["description"]}

## 位置
- **文件**: `{issue["file"]}`
- **行号**: {issue.get("line", "N/A")}

## 代码片段
```python
{issue.get("code", "N/A")}
```

## 修复建议
{issue.get("suggestion", "待 AI 生成")}

---
**AI 元数据**
- 生成时间: {datetime.now().isoformat()}
- 扫描器: {self.client.model}
- 文件: {issue["file"]}
"""

        labels = [priority]
        return create_issue(title, body, labels)

    def run(self, directory: str = ".") -> None:
        """Run the scanner.

        Args:
            directory: Directory to scan (default: src)
        """
        logger.info(f"Starting scan of {directory}")

        # Scan for issues
        issues = self.scan_directory(directory)
        logger.info(f"Found {len(issues)} total issues")

        # Deduplicate
        issues = self.deduplicate_issues(issues)
        logger.info(f"After deduplication: {len(issues)} issues")

        # Filter existing
        issues = self.filter_existing_issues(issues)
        logger.info(f"New issues: {len(issues)}")

        if not issues:
            logger.info("No new issues to create")
            return

        # Ensure diverse distribution across priorities
        issues = self.ensure_diverse_distribution(issues)

        # Create issues
        for issue in issues:
            if self.created >= self.max_issues:
                break

            try:
                issue_number = self.create_issue_from_data(issue)
                self.created += 1
                priority = issue.get("severity", "p2")
                logger.info(f"Created #{issue_number} [{priority}] - {issue.get('description', '')[:50]}")
            except Exception as e:
                logger.error(f"Failed to create issue: {e}")

        logger.info(f"Scan complete: {self.created} issues created")


def main():
    """Main entry point."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    scanner = Scanner()

    # Get target directory from environment or default
    target_dir = os.getenv("TARGET_DIR", "src")

    if not Path(target_dir).exists():
        logger.warning(f"Target directory not found: {target_dir}")
        logger.info("Creating target-project directory...")
        Path(target_dir).mkdir(parents=True, exist_ok=True)

    scanner.run(target_dir)


if __name__ == "__main__":
    main()
