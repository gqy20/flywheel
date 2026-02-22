"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Pre-computed translation table for control characters that need \xNN escaping
# Maps code point -> escaped string (or None for characters that pass through)
# This is computed once at module load for optimal performance
_CONTROL_CHAR_TRANSLATION: dict[int, str | None] = {}

for code in range(0x100):
    if (0 <= code <= 0x1f and code not in (0x0A, 0x0D, 0x09)) or 0x7F <= code <= 0x9F:
        # Control characters (excluding \n, \r, \t) that need \xNN escaping
        _CONTROL_CHAR_TRANSLATION[code] = f"\\x{code:02x}"
    # Characters not in the dict (None mapping) pass through unchanged


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
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Use str.translate() with pre-computed table for O(n) C-level performance
    text = text.translate(_CONTROL_CHAR_TRANSLATION)

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
