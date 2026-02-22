"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode BiDi and invisible formatting characters:
    - U+200B-U+200F: Zero-width chars and directional marks
    - U+202A-U+202E: Bidirectional text embeddings/overrides
    - U+2060-U+2069: Word joiner, invisible operators, and directional isolates
    - U+FEFF: BOM / Zero-width no-break space
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

    # Helper to check if a codepoint is a dangerous Unicode character
    def is_dangerous_unicode(code: int) -> bool:
        """Check if codepoint is a BiDi or invisible formatting character."""
        # BiDi embeddings/overrides: U+202A-U+202E
        if 0x202A <= code <= 0x202E:
            return True
        # BiDi isolates: U+2066-U+2069
        if 0x2066 <= code <= 0x2069:
            return True
        # Zero-width and directional marks: U+200B-U+200F
        if 0x200B <= code <= 0x200F:
            return True
        # Invisible operators: U+2060-U+2064
        if 0x2060 <= code <= 0x2064:
            return True
        # BOM / Zero-width no-break space: U+FEFF
        if code == 0xFEFF:
            return True
        return False

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    # Also escape dangerous Unicode characters with \\uXXXX
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        elif is_dangerous_unicode(code):
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
