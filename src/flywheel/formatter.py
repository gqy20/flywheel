"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode bidirectional formatting characters (U+202A-U+202E,
    U+200E-U+200F, U+2066-U+2069) and zero-width characters (U+200B-U+200D,
    U+2060, U+FEFF) to prevent visual spoofing/Trojan Source attacks.
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

    # Characters that should be escaped with \\uXXXX format
    # - Control chars (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), C1 (0x80-0x9f)
    # - Bidirectional formatting: U+202A-U+202E, U+200E-U+200F, U+2066-U+2069
    # - Zero-width chars: U+200B-U+200D, U+2060, U+FEFF
    result = []
    for char in text:
        code = ord(char)
        # C0 control chars (excluding \n, \r, \t), DEL, and C1 control chars
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        # Bidirectional and zero-width characters (Trojan Source / visual spoofing prevention)
        elif code in (
            0x200B, 0x200C, 0x200D,  # Zero-width chars: ZWSP, ZWNJ, ZWJ
            0x200E, 0x200F,  # Directional marks: LRM, RLM
            0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # Bidi formatting: LRE, RLE, PDF, LRO, RLO
            0x2060,  # Word Joiner
            0x2066, 0x2067, 0x2068, 0x2069,  # Isolate controls: LRI, RLI, FSI, PDI
            0xFEFF,  # BOM / Zero-Width No-Break Space
        ):
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
