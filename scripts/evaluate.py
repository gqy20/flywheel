"""Evaluate and prioritize issues."""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.utils import get_issues, setup_logging, update_issue_labels

logger = logging.getLogger(__name__)

# Priority scores
PRIORITY_SCORES = {
    "p0": 100,
    "p1": 75,
    "p2": 50,
    "p3": 25,
}


class PriorityEvaluator:
    """Evaluate and prioritize issues."""

    def __init__(self) -> None:
        pass

    def calculate_score(self, issue: dict) -> int:
        """Calculate priority score for an issue.

        Args:
            issue: Issue dictionary from gh CLI

        Returns:
            Priority score
        """
        score = 0

        # Base priority from label
        for label in issue.get("labels", []):
            label_name = label.get("name", "")
            if label_name in PRIORITY_SCORES:
                score += PRIORITY_SCORES[label_name]
                break

        # Type bonus (from title)
        title = issue.get("title", "").lower()
        if "[security]" in title or "安全" in title:
            score += 30
        elif "[bug]" in title or "缺陷" in title:
            score += 20
        elif "[perf]" in title or "性能" in title or "[test]" in title:
            score += 10
        elif "[refactor]" in title:
            score += 5
        elif "[docs]" in title:
            score += 0

        # Age bonus (older issues get higher priority)
        # Note: gh CLI doesn't provide created_at by default, skip for now

        return score

    def sort_issues(self, issues: list[dict]) -> list[tuple[int, dict]]:
        """Sort issues by priority score.

        Args:
            issues: List of issue dictionaries

        Returns:
            List of (score, issue) tuples, sorted by score descending
        """
        scored_issues = [(self.calculate_score(issue), issue) for issue in issues]
        scored_issues.sort(key=lambda x: x[0], reverse=True)
        return scored_issues

    def update_priority_labels(self) -> None:
        """Update priority labels based on current evaluation.

        This ensures labels stay in sync with actual priority.
        """
        issues = get_issues(state="open")

        for score, issue in self.sort_issues(issues):
            # Determine target priority label
            if score >= 80:
                target_label = "p0"
            elif score >= 50:
                target_label = "p1"
            elif score >= 30:
                target_label = "p2"
            else:
                target_label = "p3"

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
        scored_issues = self.sort_issues(issues)

        print("\n=== Priority Report ===")
        print(f"Total open issues: {len(issues)}")
        print()

        # Count by priority
        priority_counts = {"p0": 0, "p1": 0, "p2": 0, "p3": 0}
        for issue in issues:
            for label in issue.get("labels", []):
                label_name = label.get("name", "")
                if label_name in priority_counts:
                    priority_counts[label_name] += 1
                    break

        print("Priority Distribution:")
        for priority in ["p0", "p1", "p2", "p3"]:
            count = priority_counts[priority]
            bar = "█" * count
            print(f"  {priority}: {bar} ({count})")

        print()
        print("Top 10 Issues by Priority:")
        print()

        for i, (score, issue) in enumerate(scored_issues[:10], 1):
            title = issue.get("title", "Untitled")
            number = issue.get("number", "?")
            url = issue.get("url", "")

            # Get priority label
            priority = "p3"
            for label in issue.get("labels", []):
                label_name = label.get("name", "")
                if label_name in PRIORITY_SCORES:
                    priority = label_name
                    break

            print(f"{i:2d}. [{priority}] #{number} (score: {score})")
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
