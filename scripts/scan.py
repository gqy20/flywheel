"""Scan code and create issues."""

import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

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
    "Feature": "p2",  # 功能增强通常为中优先级
    "Enhancement": "p2",  # 改进建议
}

type IssueData = dict[str, Any]


class Scanner:
    """Code scanner that finds issues using Claude."""

    def __init__(self) -> None:
        self.client = ClaudeClient()
        self.max_issues = int(os.getenv("MAX_ISSUES", "3"))
        self.created = 0

    def scan_file(self, filepath: str) -> list[IssueData]:
        """Scan a single file for issues.

        Args:
            filepath: Path to file

        Returns:
            List of found issues
        """
        if not Path(filepath).exists():
            logger.warning(f"File does not exist: {filepath}")
            return []

        logger.info(f"Scanning {filepath}")

        issues = self.client.analyze_code(filepath)
        logger.info(f"Found {len(issues)} issues in {filepath}")

        # Add filepath to each issue
        for issue in issues:
            issue["file"] = filepath

        return issues

    def scan_opportunities(self, filepath: str) -> list[IssueData]:
        """Scan a single file for enhancement opportunities.

        Args:
            filepath: Path to file

        Returns:
            List of found opportunities
        """
        if not Path(filepath).exists():
            logger.warning(f"File does not exist: {filepath}")
            return []

        logger.info(f"Scanning opportunities in {filepath}")

        opportunities = self.client.analyze_opportunities(filepath)
        logger.info(f"Found {len(opportunities)} opportunities in {filepath}")

        # Add filepath to each opportunity
        for opp in opportunities:
            if not opp.get("file"):
                opp["file"] = filepath

        return opportunities

    def scan_directory(
        self, directory: str, patterns: list[str] | None = None
    ) -> tuple[list[IssueData], list[IssueData]]:
        """Scan directory for issues and opportunities.

        Args:
            directory: Directory to scan
            patterns: File patterns to include (default: *.py)

        Returns:
            Tuple of (problems list, opportunities list)
        """
        if patterns is None:
            patterns = ["*.py"]

        all_problems: list[IssueData] = []
        all_opportunities: list[IssueData] = []
        base_path = Path(directory)

        for pattern in patterns:
            for filepath in base_path.rglob(pattern):
                if self.created >= self.max_issues:
                    logger.info(f"Reached max issues limit: {self.max_issues}")
                    return all_problems, all_opportunities

                # Scan for problems
                problems = self.scan_file(str(filepath))
                all_problems.extend(problems)

                # Scan for opportunities
                opportunities = self.scan_opportunities(str(filepath))
                all_opportunities.extend(opportunities)

        return all_problems, all_opportunities

    def deduplicate_issues(self, issues: list[IssueData]) -> list[IssueData]:
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

    def filter_existing_issues(self, issues: list[IssueData]) -> list[IssueData]:
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

    def ensure_diverse_distribution(self, issues: list[IssueData]) -> list[IssueData]:
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
        selected: list[IssueData] = []
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
        dist: defaultdict[str, int] = defaultdict(int)
        for issue in selected:
            dist[issue.get("severity", "p2")] += 1
        logger.info(f"Issue distribution: {dict(dist)}")

        return selected

    def create_issue_from_data(self, issue: IssueData) -> int:
        """Create a GitHub issue from issue data.

        Args:
            issue: Issue dictionary

        Returns:
            Issue number
        """
        title = f"[{issue['type']}] {issue['description'][:80]}"
        priority = issue.get("severity", "p2")

        # 根据类型选择对应的模板格式
        issue_type = issue.get("type", "").lower()

        if issue_type in ["bug", "security"]:
            # Bug Report 模板格式
            body = f"""**问题描述**
{issue["description"]}

**位置**
- 文件: `{issue["file"]}`
- 行号: {issue.get("line", "N/A")}

**代码片段**
```python
{issue.get("code", "N/A")}
```

**修复建议**
{issue.get("suggestion", "待 AI 生成")}

---
*AI 扫描器生成 • {self.client.model} • {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        elif issue_type in ["perf", "refactor", "test"]:
            # Feature/Improvement 模板格式
            body = f"""**功能描述**
{issue["description"]}

**涉及文件**
`{issue["file"]}`

**当前代码**
```python
{issue.get("code", "N/A")}
```

**改进建议**
{issue.get("suggestion", "待 AI 生成")}

**优先级**
{priority.upper()}

---
*AI 扫描器生成 • {self.client.model} • {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        elif issue_type in ["feature", "enhancement"]:
            # Feature/Enhancement 专用模板格式
            body = f"""**功能描述**
{issue["description"]}

**价值**
{issue.get("value", "改进用户体验或开发效率")}

**涉及文件**
`{issue["file"]}`

**实现建议**
{issue.get("suggestion", "待补充实现细节")}

**优先级**
{priority.upper()}

---
*AI 扫描器生成 • {self.client.model} • {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        else:
            # Docs/Other 模板格式
            body = f"""**描述**
{issue["description"]}

**相关文件**
{issue["file"]}

**建议**
{issue.get("suggestion", "待补充")}

---
*AI 扫描器生成 • {self.client.model} • {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""

        labels = [priority]
        return create_issue(title, body, labels)

    def run(self, directory: str = ".") -> None:
        """Run the scanner.

        Args:
            directory: Directory to scan (default: src)
        """
        logger.info(f"Starting scan of {directory}")

        # Scan for both problems and opportunities
        problems, opportunities = self.scan_directory(directory)
        logger.info(f"Found {len(problems)} problems and {len(opportunities)} opportunities")

        # Deduplicate separately
        problems = self.deduplicate_issues(problems)
        opportunities = self.deduplicate_issues(opportunities)
        logger.info(
            f"After deduplication: {len(problems)} problems, {len(opportunities)} opportunities"
        )

        # Filter existing issues
        problems = self.filter_existing_issues(problems)
        opportunities = self.filter_existing_issues(opportunities)
        logger.info(f"New problems: {len(problems)}, new opportunities: {len(opportunities)}")

        # Balance distribution: 3 problems + 2 opportunities
        selected_issues: list[IssueData] = []
        max_problems = 3
        max_opportunities = 2

        # Add problems (priority-sorted)
        problems_with_priority: list[tuple[str, IssueData]] = []
        for p in problems:
            priority = self.get_priority_for_type(p.get("type", ""))
            p["severity"] = priority
            problems_with_priority.append((priority, p))
        # Sort by priority (p0 first)
        problems_with_priority.sort(key=lambda x: ["p0", "p1", "p2", "p3"].index(x[0]))
        for _, p in problems_with_priority[:max_problems]:
            selected_issues.append(p)

        # Add opportunities
        for opp in opportunities[:max_opportunities]:
            priority = self.get_priority_for_type(opp.get("type", ""))
            opp["severity"] = priority
            selected_issues.append(opp)

        if not selected_issues:
            logger.info("No new issues to create")
            return

        logger.info(f"Selected {len(selected_issues)} issues for creation")

        # Create issues
        for issue in selected_issues:
            if self.created >= self.max_issues:
                break

            try:
                issue_number = self.create_issue_from_data(issue)
                self.created += 1
                priority = issue.get("severity", "p2")
                issue_type = issue.get("type", "")
                logger.info(
                    f"Created #{issue_number} [{issue_type}/{priority}] - {issue.get('description', '')[:50]}"
                )
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
