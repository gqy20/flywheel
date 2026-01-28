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
        from dataclasses import asdict

        formatted_todos = []
        for t in todos:
            try:
                # Try to use to_dict() method if available
                if hasattr(t, 'to_dict') and callable(getattr(t, 'to_dict')):
                    todo_dict = t.to_dict()
                    # Validate that to_dict() returns a dictionary
                    if isinstance(todo_dict, dict):
                        formatted_todos.append(todo_dict)
                    else:
                        # Fallback to dataclasses.asdict if to_dict() returns non-dict
                        formatted_todos.append(asdict(t))
                else:
                    # Fallback to dataclasses.asdict for dataclass objects
                    formatted_todos.append(asdict(t))
            except (TypeError, AttributeError) as e:
                # If serialization fails, use vars() as last resort
                try:
                    formatted_todos.append(vars(t))
                except Exception:
                    # If all else fails, create a minimal dict with common attributes
                    formatted_todos.append({
                        'id': getattr(t, 'id', None),
                        'title': getattr(t, 'title', str(t)),
                    })

        return json.dumps(formatted_todos, indent=2)

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
