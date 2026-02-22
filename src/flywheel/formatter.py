"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), and bidirectional Unicode control characters
    with their escaped representations to prevent injection attacks via todo text.

    Bidi control characters sanitized:
    - U+200E-U+200F: LRM/RLM (Left-to-right/Right-to-left marks)
    - U+202A-U+202E: Bidi embedding/override controls
    - U+2066-U+2069: Bidi isolate controls
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

    # Bidi control character ranges that should be escaped
    # These can be used for text direction spoofing attacks
    bidi_ranges = [
        (0x200E, 0x200F),  # LRM/RLM
        (0x202A, 0x202E),  # Bidi embedding/override
        (0x2066, 0x2069),  # Bidi isolate
    ]

    def is_bidi_control(code: int) -> bool:
        """Check if codepoint is a bidirectional control character."""
        return any(start <= code <= end for start, end in bidi_ranges)

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Also escape bidi control characters
    # Replace with \\xNN or \\uXXXX escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1F and char not in ("\n", "\r", "\t")) or 0x7F <= code <= 0x9F:
            result.append(f"\\x{code:02x}")
        elif is_bidi_control(code):
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
