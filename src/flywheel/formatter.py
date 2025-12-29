"""Output formatter for todos."""

from enum import Enum

from flywheel.todo import Priority, Status, Todo


class FormatType(str, Enum):
    """Output format types."""

    TABLE = "table"
    JSON = "json"
    COMPACT = "compact"


class Formatter:
    """Format todos for display."""

    def __init__(self, format_type: FormatType = FormatType.TABLE):
        self.format_type = format_type

    def format(self, todos: list[Todo]) -> str:
        """Format todos for display."""
        if not todos:
            return "No todos found."

        if self.format_type == FormatType.JSON:
            return self._format_json(todos)
        elif self.format_type == FormatType.COMPACT:
            return self._format_compact(todos)
        return self._format_table(todos)

    def _format_table(self, todos: list[Todo]) -> str:
        """Format as table."""
        lines = []
        lines.append(f"{'ID':<4} {'Status':<12} {'Priority':<10} {'Title'}")
        lines.append("-" * 80)

        for todo in todos:
            status_icon = self._status_icon(todo.status)
            priority_icon = self._priority_icon(todo.priority)
            lines.append(f"{todo.id:<4} {status_icon:<12} {priority_icon:<10} {todo.title}")

        return "\n".join(lines)

    def _format_compact(self, todos: list[Todo]) -> str:
        """Format as compact list."""
        return "\n".join(f"[{t.id}] {t.title}" for t in todos)

    def _format_json(self, todos: list[Todo]) -> str:
        """Format as JSON."""
        import json

        return json.dumps([t.to_dict() for t in todos], indent=2)

    def _status_icon(self, status: Status) -> str:
        """Get icon for status."""
        icons = {
            Status.TODO: "[ ]",
            Status.IN_PROGRESS: "[~]",
            Status.DONE: "[x]",
        }
        return icons.get(status, "[?]")

    def _priority_icon(self, priority: Priority) -> str:
        """Get icon for priority."""
        icons = {
            Priority.HIGH: "🔴",
            Priority.MEDIUM: "🟡",
            Priority.LOW: "🟢",
        }
        return icons.get(priority, "⚪")
