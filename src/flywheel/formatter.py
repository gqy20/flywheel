"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Pre-computed translation table for single-pass control character escaping
# Maps character ordinals to their escaped string representations
_ESCAPE_TABLE: dict[int, str] = {}

# Backslash (must be escaped first to prevent collision)
_ESCAPE_TABLE[ord("\\")] = "\\\\"

# Common control characters with readable escapes
_ESCAPE_TABLE[ord("\n")] = "\\n"
_ESCAPE_TABLE[ord("\r")] = "\\r"
_ESCAPE_TABLE[ord("\t")] = "\\t"

# C0 control characters (0x00-0x1f) excluding \n, \r, \t - use \xNN format
for code in range(0x00, 0x20):
    if code not in (ord("\n"), ord("\r"), ord("\t")):
        _ESCAPE_TABLE[code] = f"\\x{code:02x}"

# DEL (0x7f) and C1 control characters (0x80-0x9f)
for code in range(0x7F, 0xA0):
    _ESCAPE_TABLE[code] = f"\\x{code:02x}"


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses a pre-computed lookup table for single-pass processing,
    avoiding multiple string iterations for better performance.
    """
    # Single-pass: use translation table to escape all special characters
    result = []
    for char in text:
        escaped = _ESCAPE_TABLE.get(ord(char))
        if escaped:
            result.append(escaped)
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
