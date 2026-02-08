"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), bidirectional override characters (U+202A-U+202E,
    U+2066-U+2069), and zero-width characters (U+200B-U+200D, U+FEFF) with
    their escaped representations to prevent injection and text spoofing
    attacks via todo text.
    """
    result = []
    for char in text:
        code = ord(char)
        # Literal backslash - must be first to prevent collision with escape sequences
        if char == "\\":
            result.append("\\\\")
        # Common control characters - use readable escapes
        elif char == "\n":
            result.append("\\n")
        elif char == "\r":
            result.append("\\r")
        elif char == "\t":
            result.append("\\t")
        # ASCII C0 control (excluding whitespace), DEL, and C1 control
        elif (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        # Bidirectional override characters (U+202A-U+202E), bidirectional isolate
        # characters (U+2066-U+2069), zero-width characters (U+200B-U+200D),
        # and zero-width no-break space/BOM (U+FEFF)
        elif 0x200b <= code <= 0x200d or code == 0xfeff or 0x202a <= code <= 0x202e or 0x2066 <= code <= 0x2069:
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
