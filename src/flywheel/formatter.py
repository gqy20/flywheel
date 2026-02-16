"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Precomputed replacement map for single-pass sanitization
# Maps control character ordinals to their escaped string representations
_SANITZE_REPLACEMENTS: dict[int, str] = {
    # Backslash must be escaped first (handled by checking char == '\\' explicitly)
    ord("\\"): "\\\\",
    # Common control characters with readable escapes
    ord("\n"): "\\n",
    ord("\r"): "\\r",
    ord("\t"): "\\t",
}
# Build map for other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), C1 (0x80-0x9f)
for code in range(0x00, 0x20):
    if code not in (ord("\n"), ord("\r"), ord("\t")):
        _SANITZE_REPLACEMENTS[code] = f"\\x{code:02x}"
for code in range(0x7f, 0xa0):  # DEL (0x7f) and C1 (0x80-0x9f)
    _SANITZE_REPLACEMENTS[code] = f"\\x{code:02x}"


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses a single-pass approach with a precomputed replacement map for O(n)
    performance, avoiding intermediate string creation from repeated replace() calls.
    """
    # Single-pass: iterate once and build result
    result = []
    for char in text:
        if char == "\\":
            # Backslash must be escaped first to prevent collision
            result.append("\\\\")
        elif ord(char) in _SANITZE_REPLACEMENTS:
            result.append(_SANITZE_REPLACEMENTS[ord(char)])
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
