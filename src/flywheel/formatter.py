"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode bidirectional override characters that can be
    used for display spoofing attacks:
    - U+202A-U+202E: Bidirectional embedding/override controls
    - U+2066-U+2069: Bidirectional isolate controls
    - U+200E-U+200F: Directional marks (LRM, RLM)
    - U+FEFF: BOM / Zero Width No-Break Space
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

    # Unicode bidirectional/format characters that can be used for spoofing
    # These ranges contain characters that affect text display direction
    bidi_ranges = [
        (0x202A, 0x202E),  # LRE, RLE, PDF, LRO, RLO
        (0x2066, 0x2069),  # LRI, RLI, FSI, PDI
        (0x200E, 0x200F),  # LRM, RLM
        (0xFEFF, 0xFEFF),  # BOM / Zero Width No-Break Space
    ]

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    # Unicode bidi characters are replaced with \\uXXXX escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        elif any(start <= code <= end for start, end in bidi_ranges):
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
