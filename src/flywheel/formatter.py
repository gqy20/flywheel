"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes bidirectional (Bidi) Unicode control characters to prevent
    text direction spoofing attacks:
    - U+200E-U+200F: LRM, RLM (directional marks)
    - U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (bidirectional formatting)
    - U+2066-U+2069: LRI, RLI, FSI, PDI (isolate controls)
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

    # Check if a code point is a bidirectional control character
    def is_bidi_control(code: int) -> bool:
        return (
            code in (0x200E, 0x200F)  # LRM, RLM
            or 0x202A <= code <= 0x202E  # LRE, RLE, PDF, LRO, RLO
            or 0x2066 <= code <= 0x2069  # LRI, RLI, FSI, PDI
        )

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), C1 (0x80-0x9f),
    # and Bidi controls
    # Replace with \\xNN or \\uNNNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
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
