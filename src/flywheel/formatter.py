"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes Unicode BiDi (bidirectional) characters and invisible
    formatting characters to prevent text display manipulation attacks:
    - U+202A-U+202E: BiDi override/embedding characters
    - U+2066-U+2069: BiDi isolate characters
    - U+200B-U+200F, U+2060-U+2064, U+FEFF: Invisible formatting characters
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

    # Unicode ranges for dangerous formatting characters:
    # - 0x00-0x1f: C0 control chars (excluding \n, \r, \t which are handled above)
    # - 0x7f-0x9f: DEL and C1 control chars
    # - 0x200b-0x200f: Zero-width chars and directional marks
    # - 0x202a-0x202e: BiDi override/embedding chars (security risk)
    # - 0x2060-0x2069: Word joiner and BiDi isolate chars
    # - 0xfeff: Byte Order Mark / Zero Width No-Break Space
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or (0x7f <= code <= 0x9f):
            # Use \xNN format for ASCII control chars (C0, DEL, C1)
            result.append(f"\\x{code:02x}")
        elif (
            (0x200b <= code <= 0x200f)
            or (0x202a <= code <= 0x202e)
            or (0x2060 <= code <= 0x2069)
            or code == 0xFEFF
        ):
            # Use \uNNNN format for Unicode formatting chars
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
