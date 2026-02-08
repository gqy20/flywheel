"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), and Unicode bidirectional override characters
    with their escaped representations to prevent injection attacks via todo text.
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

    # Control characters to escape:
    # - ASCII/C1 controls: (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), C1 (0x80-0x9f)
    # - Unicode bidi overrides: U+202A-U+202E (LRE, RLE, PDF, LRO, RLO)
    # - Zero-width chars: U+200B-U+200D (ZWSP, ZWNJ, ZWJ)
    # - Bidi isolation: U+2066-U+2069 (LRI, RLI, FSI, PDI)
    result = []
    for char in text:
        code = ord(char)
        is_ascii_control = (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f
        is_unicode_bidi_control = (
            0x202a <= code <= 0x202e or  # Bidirectional overrides
            0x200b <= code <= 0x200d or  # Zero-width characters
            0x2066 <= code <= 0x2069     # Bidirectional isolation
        )

        if is_ascii_control:
            # Use \xNN format for ASCII/C1 control characters
            result.append(f"\\x{code:02x}")
        elif is_unicode_bidi_control:
            # Use \uNNNN format for Unicode control characters
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
