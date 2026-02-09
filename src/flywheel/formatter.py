"""Output formatter for todo data."""

from __future__ import annotations

from datetime import UTC, datetime

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
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)

        # Add overdue indicator or due date
        suffix = ""
        if todo.due_date and not todo.done:
            # Check if overdue
            try:
                from datetime import date

                due = date.fromisoformat(todo.due_date)
                today = datetime.now(UTC).date()
                suffix = " [OVERDUE]" if due < today else f" [due: {todo.due_date}]"
            except ValueError:
                # Invalid date format, just show the raw value
                suffix = f" [due: {todo.due_date}]"
        elif todo.due_date and todo.done:
            # Completed tasks show their due date without OVERDUE
            suffix = f" [due: {todo.due_date}]"

        return f"[{status}] {todo.id:>3} {safe_text}{suffix}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
