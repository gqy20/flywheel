"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Remove dangerous control characters that could cause terminal injection.

    Removes:
    - Newline (\\n), carriage return (\\r), tab (\\t)
    - Null byte (\\x00)
    - ANSI escape sequences (\\x1b/ESC)

    Args:
        text: The text to sanitize.

    Returns:
        The sanitized text with dangerous control characters removed.
    """
    # Define dangerous control characters to remove
    dangerous_chars = ["\n", "\r", "\t", "\x00", "\x1b"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    return text


class TodoFormatter:
    """Render todos in simple text tables."""

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)
        return f"[{status}] {todo.id:>3} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
