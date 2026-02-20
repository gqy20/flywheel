"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Uses a single-pass approach with str.translate for optimal performance
    on large inputs, avoiding O(n*k) string copies from multiple replace() calls.
    """
    # Build translation table for single-pass processing
    # str.translate maps ord(char) -> replacement string (or None to delete)

    # Create translation table
    trans_table = {}

    # Common control characters with readable escapes
    trans_table[ord("\n")] = "\\n"
    trans_table[ord("\r")] = "\\r"
    trans_table[ord("\t")] = "\\t"

    # Other C0 control characters (0x00-0x1f, excluding \n \r \t) -> hex escape
    for code in range(0x00, 0x20):
        if code not in (ord("\n"), ord("\r"), ord("\t")):
            trans_table[code] = f"\\x{code:02x}"

    # DEL (0x7f) and C1 control characters (0x80-0x9f) -> hex escape
    for code in range(0x7F, 0xA0):
        trans_table[code] = f"\\x{code:02x}"

    # Backslash must be escaped to prevent collision with escape sequences
    trans_table[ord("\\")] = "\\\\"

    # Single-pass translation
    return text.translate(trans_table)


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
