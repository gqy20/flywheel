"""Output formatter for todo data."""

from __future__ import annotations

from datetime import UTC, datetime

from .todo import Todo


def _is_overdue(todo: Todo) -> bool:
    """Check if a todo is overdue (past due date and not done).

    Args:
        todo: The todo to check.

    Returns:
        True if the todo is overdue, False otherwise.
    """
    if todo.due_date is None or todo.done:
        return False
    try:
        due_dt = datetime.fromisoformat(todo.due_date)
        # Reset due_dt to midnight for consistent comparison
        due_dt = due_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get current date in UTC
        now_utc = datetime.now(UTC)

        # Convert due_dt to UTC for comparison (assume naive dates are UTC)
        due_dt_utc = (
            due_dt.replace(tzinfo=UTC) if due_dt.tzinfo is None else due_dt.astimezone(UTC)
        )

        # Compare dates only
        due_date_only = due_dt_utc.date()
        now_date_only = now_utc.date()

        return due_date_only < now_date_only
    except (ValueError, AttributeError):
        # If we can't parse the date, don't mark as overdue
        return False


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.
    """
    # First: Escape backslash to prevent collision with escape sequences
    # This MUST be done before any other escaping to prevent ambiguity
    # between literal backslash-escape text and sanitized control characters.
    text = text.replace("\\", "\\\\")

    # Common control characters - replace with readable escapes
    replacements = [
        ("\n", "\\n"),
        ("\r", "\\r"),
        ("\t", "\\t"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        else:
            result.append(char)
    return "".join(result)


class TodoFormatter:
    """Render todos in simple text tables."""

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)

        # Add overdue prefix for incomplete tasks past their due date
        prefix = ""
        if _is_overdue(todo):
            prefix = "OVERDUE "

        # Add due date if present
        due_suffix = ""
        if todo.due_date:
            due_suffix = f" (due: {todo.due_date})"

        return f"[{status}] {todo.id:>3} {prefix}{safe_text}{due_suffix}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
