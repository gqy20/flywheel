"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode bidirectional and zero-width characters to prevent
    visual spoofing/Trojan Source attacks:
    - U+200B-U+200F: Zero-width space, non-joiner, joiner, and direction marks
    - U+202A-U+202E: Bidirectional override controls (LRE, RLE, PDF, LRO, RLO)
    - U+2060: Word joiner
    - U+FEFF: Byte Order Mark / Zero-width no-break space
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
    # Also escape Unicode bidi/zero-width chars with \\uXXXX for visual safety
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        # Zero-width, bidi controls, word joiner, BOM - escape to prevent visual spoofing
        elif (
            0x200B <= code <= 0x200F  # ZW space/non-joiner/joiner + LRM/RLM
            or 0x202A <= code <= 0x202E  # Bidirectional overrides (LRE, RLE, PDF, LRO, RLO)
            or code == 0x2060  # Word joiner
            or code == 0xFEFF  # BOM / Zero-width no-break space
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
