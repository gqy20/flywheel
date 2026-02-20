"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Single-pass implementation for O(n) performance (Issue #4708).
    """
    # Mapping for common control characters with readable escapes
    common_escapes = {
        ord("\\"): "\\\\",
        ord("\n"): "\\n",
        ord("\r"): "\\r",
        ord("\t"): "\\t",
    }

    result = []
    for char in text:
        code = ord(char)
        # Check common escapes first (backslash, \n, \r, \t)
        if code in common_escapes:
            result.append(common_escapes[code])
        # Other control characters: 0x00-0x1f (excluding handled above), DEL (0x7f), C1 (0x80-0x9f)
        elif code <= 0x1f or 0x7f <= code <= 0x9f:
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
