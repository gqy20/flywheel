"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.

    Also escapes BiDi (Bidirectional) override characters (U+202A-U+202E, U+2066-U+2069)
    to prevent text direction spoofing attacks.
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

    # BiDi override characters that enable text direction spoofing
    # U+202A-U+202E: LRE, RLE, PDF, LRO, RLO
    # U+2066-U+2069: LRI, RLI, FSI, PDI
    bidi_chars = {
        "\u202a": "\\u202a",  # LRE - Left-to-Right Embedding
        "\u202b": "\\u202b",  # RLE - Right-to-Left Embedding
        "\u202c": "\\u202c",  # PDF - Pop Directional Format
        "\u202d": "\\u202d",  # LRO - Left-to-Right Override
        "\u202e": "\\u202e",  # RLO - Right-to-Left Override
        "\u2066": "\\u2066",  # LRI - Left-to-Right Isolate
        "\u2067": "\\u2067",  # RLI - Right-to-Left Isolate
        "\u2068": "\\u2068",  # FSI - First Strong Isolate
        "\u2069": "\\u2069",  # PDI - Pop Directional Isolate
    }

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
        elif char in bidi_chars:
            result.append(bidi_chars[char])
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
