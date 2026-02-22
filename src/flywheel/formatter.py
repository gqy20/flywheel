"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Pre-built translation table for control character escaping
# Built once at module load for O(1) lookup during sanitization
_CONTROL_CHAR_TABLE = {
    i: f"\\x{i:02x}" for i in range(0x100) if (i <= 0x1F or 0x7F <= i <= 0x9F)
}

# Override common control characters with readable escapes
_CONTROL_CHAR_TABLE[ord("\n")] = "\\n"
_CONTROL_CHAR_TABLE[ord("\r")] = "\\r"
_CONTROL_CHAR_TABLE[ord("\t")] = "\\t"

# Remove backslash from the table - it's handled separately first
_CONTROL_CHAR_TABLE.pop(ord("\\"), None)


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

    # Use str.translate for efficient control character replacement
    return text.translate(_CONTROL_CHAR_TABLE)


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
