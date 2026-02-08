"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), Unicode bidirectional override characters
    (U+202A-U+202E), and zero-width characters (U+200B-U+200D) with their
    escaped representations to prevent injection attacks via todo text.
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

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f),
    # C1 (0x80-0x9f), Unicode bidirectional overrides (U+202A-U+202E),
    # and zero-width characters (U+200B-U+200D)
    # Replace with \\xNN (for code <= 0xff) or \\uNNNN (for code > 0xff) escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (
            (0 <= code <= 0x1f and char not in ("\n", "\r", "\t"))
            or 0x7f <= code <= 0x9f
            or 0x200b <= code <= 0x200d
            or 0x202a <= code <= 0x202e
        ):
            if code <= 0xff:
                result.append(f"\\x{code:02x}")
            else:
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
