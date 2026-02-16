"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), bidirectional formatting characters (U+202A-U+202E,
    U+200E, U+200F), and zero-width/invisible characters (U+200B-U+200D, U+2060,
    U+FEFF) with their escaped representations to prevent injection attacks
    and visual spoofing (Trojan Source) via todo text.
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

    # Ranges of characters that need sanitization:
    # - C0 controls (0x00-0x1f excluding \n, \r, \t)
    # - DEL (0x7f)
    # - C1 controls (0x80-0x9f)
    # - Zero-width and direction marks (U+200B-U+200F)
    # - Word joiner (U+2060)
    # - Bidirectional formatting (U+202A-U+202E)
    # - BOM/Zero-width no-break space (U+FEFF)
    def needs_escape(code: int) -> bool:
        if (0 <= code <= 0x1F) or (0x7F <= code <= 0x9F):
            return True
        if 0x200B <= code <= 0x200F:  # Zero-width chars and direction marks
            return True
        if code == 0x2060:  # Word joiner
            return True
        if 0x202A <= code <= 0x202E:  # Bidirectional formatting
            return True
        if code == 0xFEFF:  # BOM
            return True
        return False

    # Build result with appropriate escape sequences
    result = []
    for char in text:
        code = ord(char)
        if char in ("\n", "\\n", "\r", "\\r", "\t", "\\t"):
            # Already escaped common controls pass through
            result.append(char)
        elif needs_escape(code):
            # Use \\uNNNN for Unicode codepoints > 0xFF, \\xNN for <= 0xFF
            if code <= 0xFF:
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
