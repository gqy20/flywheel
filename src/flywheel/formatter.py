"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses a single-pass approach to avoid creating O(n*m) intermediate strings
    from repeated replace() calls (Issue #3579).
    """
    # Build mapping of characters that need special handling
    # Common control characters with readable escape sequences
    special_escapes = {
        "\\": "\\\\",  # Backslash MUST be first in this mapping
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }

    result = []
    for char in text:
        code = ord(char)
        if char in special_escapes:
            # Use readable escape sequence for common chars
            result.append(special_escapes[char])
        elif (0 <= code <= 0x1F) or (0x7F <= code <= 0x9F):
            # Other control chars: 0x00-0x1f (excluding \n, \r, \t already handled),
            # DEL (0x7f), and C1 (0x80-0x9f)
            result.append(f"\\x{code:02x}")
        else:
            # Normal character - pass through unchanged
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
