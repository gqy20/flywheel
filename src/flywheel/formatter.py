"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), and invisible/formatting Unicode characters
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

    # Zero-width and invisible Unicode characters that enable visual spoofing
    # U+200B-U+200F: Zero-width space, non-joiner, joiner, LTR mark, RTL mark
    # U+FEFF: BOM / Zero-width no-break space
    # U+2060: Word joiner
    zero_width_chars = {
        0x200B,
        0x200C,
        0x200D,
        0x200E,
        0x200F,  # ZW space, ZW non-joiner, ZW joiner, LTR, RTL marks
        0xFEFF,  # BOM
        0x2060,  # Word joiner
    }

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    # Zero-width Unicode chars are replaced with \\uNNNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1F and char not in ("\n", "\r", "\t")) or 0x7F <= code <= 0x9F:
            result.append(f"\\x{code:02x}")
        elif code in zero_width_chars:
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
