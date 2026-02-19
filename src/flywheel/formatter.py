"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Pre-computed escape table for control characters (0x00-0x1f, 0x7f-0x9f).
# Indexed by character code. None means pass through unchanged.
# This avoids f-string formatting overhead in the hot path (issue #4523).
_ESCAPE_TABLE: list[str | None] = [None] * 256
# Common control characters with readable escapes
_ESCAPE_TABLE[ord("\\")] = "\\\\"
_ESCAPE_TABLE[ord("\n")] = "\\n"
_ESCAPE_TABLE[ord("\r")] = "\\r"
_ESCAPE_TABLE[ord("\t")] = "\\t"
# Other control characters: \\xNN format
for code in range(0x00, 0x20):
    if _ESCAPE_TABLE[code] is None:
        _ESCAPE_TABLE[code] = f"\\x{code:02x}"
for code in range(0x7F, 0xA0):
    _ESCAPE_TABLE[code] = f"\\x{code:02x}"


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses a single-pass approach with pre-computed escape table for
    better performance on large strings (issue #4523).
    """
    result = []
    for char in text:
        code = ord(char)
        if code < 256:
            escaped = _ESCAPE_TABLE[code]
            if escaped is not None:
                result.append(escaped)
                continue
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
