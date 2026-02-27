"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# BiDi (Bidirectional) override characters that can be used for visual spoofing attacks
# U+202A-U+202E: LRE, RLE, PDF, LRO, RLO
# U+2066-U+2069: LRI, RLI, FSI, PDI
BIDI_CHARS = frozenset(
    chr(code) for code in range(0x202A, 0x202F)  # U+202A-U+202E
) | frozenset(chr(code) for code in range(0x2066, 0x206A))  # U+2066-U+2069


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes BiDi (Bidirectional) override characters (U+202A-U+202E, U+2066-U+2069)
    which can be used for visual spoofing attacks (e.g., making 'exe.pac' display as 'cap.exe').
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

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    # BiDi override characters - replace with \\uNNNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        elif char in BIDI_CHARS:
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
