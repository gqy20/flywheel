"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses single-pass O(n) algorithm for performance with long strings.
    """
    # Single-pass algorithm: process each character exactly once
    # This is O(n) instead of O(n*m) from multiple replace() calls
    result = []
    for char in text:
        code = ord(char)
        if char == "\\":
            # Backslash must be escaped first to prevent collision with escape sequences
            result.append("\\\\")
        elif char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        elif (0 <= code <= 0x1f) or (0x7f <= code <= 0x9f):
            # Other control characters: 0x00-0x1f (excluding \n, \r, \t already handled),
            # DEL (0x7f), and C1 (0x80-0x9f)
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
        return f"[{status}] {todo.id:>3} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
