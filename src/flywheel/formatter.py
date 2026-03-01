"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode bidirectional override characters that can be
    used for display spoofing attacks (U+202A-U+202E, U+2066-U+2069,
    U+200E-U+200F, U+FEFF).
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

    # Unicode bidirectional override characters that can be used for spoofing
    # U+202A-U+202E: Bidirectional embedding/override controls
    # U+200E-U+200F: Left-to-Right/Right-to-Left marks
    # U+2066-U+2069: Bidirectional isolate controls
    # U+FEFF: BOM / Zero Width No-Break Space (can hide content)
    bidi_chars = {
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,  # Embedding/override
        0x200E,
        0x200F,  # Directional marks
        0x2066,
        0x2067,
        0x2068,
        0x2069,  # Isolates
        0xFEFF,  # BOM/ZWNBSP
    }

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1F and char not in ("\n", "\r", "\t")) or 0x7F <= code <= 0x9F:
            result.append(f"\\x{code:02x}")
        elif code in bidi_chars:
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
