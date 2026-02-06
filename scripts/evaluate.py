"""Evaluate and prioritize issues."""

import logging
import os
import sys
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).parent))

from shared.claude import ClaudeClient
from shared.utils import get_issues, setup_logging, update_issue_labels

logger = logging.getLogger(__name__)


class PriorityEvaluator:
    """Evaluate and prioritize issues using AI."""

    # Priority scores for final label
    PRIORITY_SCORES: ClassVar[dict[str, int]] = {
        "p0": 100,
        "p1": 75,
        "p2": 50,
        "p3": 25,
    }

    def __init__(self) -> None:
        self.client = ClaudeClient()

    def ai_evaluate_priority(self, issue: dict) -> str:
        """Use AI to evaluate issue priority.

        Args:
            issue: Issue dictionary from gh CLI

        Returns:
            Priority label (p0/p1/p2/p3)
        """
        title = issue.get("title", "")
        body = issue.get("body", "")
        issue_number = issue.get("number", "?")
        logger.info(
            "AI priority evaluation start issue=#%s title=%s",
            issue_number,
            title[:80].replace("\n", " "),
        )

        prompt = f"""分析以下 GitHub issue 的优先级，返回 p0/p1/p2/p3 中的一个。

**优先级标准**:
- p0: 安全漏洞、数据丢失、严重bug、阻塞性问题
- p1: 重要bug、性能问题、核心功能缺陷
- p2: 一般bug、代码质量改进、测试覆盖
- p3: 文档、优化、重构、非功能性问题

**Issue 信息**:
标题: {title}
描述: {body[:1000]}

**只返回优先级标签（p0/p1/p2/p3），不要其他内容**。"""

        try:
            response = self.client.chat(prompt, temperature=0.1, max_tokens=10)
            # 清理响应，提取优先级标签
            priority = response.strip().lower()
            # 验证返回值是否有效
            if priority in ["p0", "p1", "p2", "p3"]:
                logger.info(
                    "AI priority evaluation done issue=#%s priority=%s", issue_number, priority
                )
                return priority
            else:
                logger.warning(f"AI returned invalid priority: {priority}, defaulting to p2")
                return "p2"
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}, defaulting to p2")
            return "p2"

    def update_priority_labels(self) -> None:
        """Update priority labels using AI evaluation.

        This ensures labels are based on actual issue content, not existing labels.
        """
        issues = get_issues(state="open")
        logger.info("Loaded %s open issues for priority evaluation", len(issues))

        for issue in issues:
            # Use AI to evaluate priority based on content
            target_label = self.ai_evaluate_priority(issue)

            # Get current labels
            current_labels = [label.get("name", "") for label in issue.get("labels", [])]

            # Update if priority has changed
            priority_labels = {"p0", "p1", "p2", "p3"}
            current_priority = set(current_labels) & priority_labels

            if current_priority != {target_label}:
                # Remove old priority labels
                labels_to_remove = list(current_priority - {target_label})

                # Build new labels list
                new_labels = [label for label in current_labels if label not in labels_to_remove]

                # Add new priority label if not present
                if target_label not in new_labels:
                    new_labels.append(target_label)

                # Update issue
                issue_number = issue.get("number")
                if issue_number:
                    try:
                        update_issue_labels(issue_number, new_labels)
                        logger.info(
                            f"Updated issue #{issue_number}: "
                            f"{''.join(current_priority)} → {target_label}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to update issue #{issue_number}: {e}")

    def print_priority_report(self) -> None:
        """Print a priority report for all issues."""
        issues = get_issues(state="open")

        print("\n=== Priority Report ===")
        print(f"Total open issues: {len(issues)}")
        print()

        # Count by priority (from AI evaluation)
        priority_counts = {"p0": 0, "p1": 0, "p2": 0, "p3": 0}
        issues_with_priority = []

        for issue in issues:
            # Use AI to evaluate priority
            priority = self.ai_evaluate_priority(issue)
            priority_counts[priority] += 1
            issues_with_priority.append((priority, issue))

        print("Priority Distribution (AI Evaluated):")
        for priority in ["p0", "p1", "p2", "p3"]:
            count = priority_counts[priority]
            bar = "█" * count
            print(f"  {priority}: {bar} ({count})")

        print()
        print("All Issues by Priority:")
        print()

        # Sort by priority (p0 first)
        priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
        issues_with_priority.sort(key=lambda x: priority_order.get(x[0], 999))

        for i, (priority, issue) in enumerate(issues_with_priority, 1):
            title = issue.get("title", "Untitled")
            number = issue.get("number", "?")

            # Get current labels
            current_labels = [label.get("name", "") for label in issue.get("labels", [])]
            priority_labels = [lbl for lbl in current_labels if lbl in priority_order]

            print(
                f"{i:2d}. [{priority}] #{number} (current: {','.join(priority_labels) if priority_labels else 'none'})"
            )
            print(f"     {title[:80]}")
            print()

    def run(self) -> None:
        """Run the evaluator."""
        logger.info("Starting priority evaluation")

        self.update_priority_labels()
        self.print_priority_report()

        logger.info("Priority evaluation complete")


def main():
    """Main entry point."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    evaluator = PriorityEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()
