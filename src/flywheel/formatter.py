"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Pre-built translation table for single-pass sanitization.
# Maps characters to their escaped string representations.
_SANITIZE_TABLE: dict[int, str] = {
    ord("\\"): "\\\\",  # Backslash must be escaped first to prevent collisions
    ord("\n"): "\\n",
    ord("\r"): "\\r",
    ord("\t"): "\\t",
}

# Add control characters (0x00-0x1f excluding \n, \r, \t) and DEL (0x7f) and C1 (0x80-0x9f)
for code in range(0x00, 0x1F + 1):
    if code not in (0x0A, 0x0D, 0x09):  # Skip \n, \r, \t
        _SANITIZE_TABLE[code] = f"\\x{code:02x}"
for code in range(0x7F, 0x9F + 1):
    _SANITIZE_TABLE[code] = f"\\x{code:02x}"


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses str.translate() for single-pass O(n) performance.
    """
    return text.translate(_SANITIZE_TABLE)


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
