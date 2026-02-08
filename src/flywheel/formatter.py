"""Output formatter for todo data."""

from __future__ import annotations

from datetime import UTC, date, datetime

from .todo import Todo


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
    def _is_overdue(due_date: str) -> bool:
        """Check if a due date is in the past (overdue).

        Args:
            due_date: ISO date string (YYYY-MM-DD).

        Returns:
            True if the due date is in the past, False otherwise.
        """
        try:
            due = date.fromisoformat(due_date)
            today = datetime.now(UTC).date()
            return due < today
        except (ValueError, TypeError):
            return False

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)

        # Build the base output
        output = f"[{status}] {todo.id:>3} {safe_text}"

        # Add due date information if present
        if todo.due_date:
            # Check if overdue
            if TodoFormatter._is_overdue(todo.due_date):
                output += f" [OVERDUE: {todo.due_date}]"
            else:
                output += f" [due: {todo.due_date}]"

        return output

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
