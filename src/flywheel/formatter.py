"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), and Unicode BiDi/invisible formatting characters
    with their escaped representations to prevent injection attacks via todo text.

    BiDi and invisible formatting characters that are escaped:
    - U+200B-U+200F: Zero-width and direction characters
    - U+202A-U+202E: Bidirectional formatting characters
    - U+2060-U+2069: Word joiner and isolate formatting characters
    - U+FEFF: Byte order mark / zero-width no-break space
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

    # Build result with escaped control characters
    # - C0 control chars (0x00-0x1f excluding \n, \r, \t)
    # - DEL (0x7f)
    # - C1 control chars (0x80-0x9f)
    # - BiDi/invisible formatting chars (see docstring)
    result = []
    for char in text:
        code = ord(char)
        # C0 controls, DEL, C1 controls
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        # Unicode BiDi and invisible formatting characters
        # - U+200B-U+200F: Zero-width and direction characters
        # - U+202A-U+202E: Bidirectional formatting characters
        # - U+2060-U+2069: Word joiner and isolate formatting characters
        # - U+FEFF: BOM / Zero-width no-break space
        elif (
            (0x200B <= code <= 0x200F)
            or (0x202A <= code <= 0x202E)
            or (0x2060 <= code <= 0x2069)
            or code == 0xFEFF
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
