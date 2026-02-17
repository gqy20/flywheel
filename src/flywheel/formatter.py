"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces the following characters with their escaped representations:
    - ASCII control characters (0x00-0x1f), except \\n, \\r, \\t
    - DEL (0x7f)
    - C1 control characters (0x80-0x9f)
    - Zero-width and directional mark characters (0x200b-0x200f)
    - Bidirectional override characters (0x202a-0x202e)

    This prevents injection attacks and text spoofing via todo text.
    """
    # First: Escape backslash to prevent collision with escape sequences
    # This MUST be done before any other escaping to prevent ambiguity
    # between literal backslash-escape text and sanitized control characters.
    text = text.replace("\\", "\\\\")

    # Common control characters - replace with readable escapes
    replacements = [
        ("\n", "\\n"),
        ("\r", "\\r"),
        ("\t", "\\t"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)

    # Other control characters to escape:
    # - (0x00-0x1f excluding \n, \r, \t): C0 controls
    # - (0x7f): DEL
    # - (0x80-0x9f): C1 controls
    # - (0x200b-0x200f): Zero-width and directional mark characters
    # - (0x202a-0x202e): Bidirectional override characters (security risk for text spoofing)
    # Replace with \\uXXXX or \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        elif 0x200b <= code <= 0x200f or 0x202a <= code <= 0x202e:
            result.append(f"\\u{code:04x}")
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
