"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), C1 control
    characters (0x80-0x9f), and Unicode bidirectional text control characters
    with their escaped representations to prevent injection attacks via todo text.

    Unicode bidirectional text control characters that are escaped:
    - U+200E-U+200F: LRM, RLM (directional marks)
    - U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (bidirectional formatting)
    - U+2028-U+2029: Line separator, paragraph separator
    - U+2066-U+2069: LRI, RLI, FSI, PDI (bidirectional isolates)
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

    # Unicode bidirectional text control characters that need escaping
    # These can be used for visual spoofing attacks
    bidi_chars = {
        # Directional marks
        "\u200e": r"\u200e",  # LRM (Left-to-Right Mark)
        "\u200f": r"\u200f",  # RLM (Right-to-Left Mark)
        # Bidirectional formatting
        "\u202a": r"\u202a",  # LRE (Left-to-Right Embedding)
        "\u202b": r"\u202b",  # RLE (Right-to-Left Embedding)
        "\u202c": r"\u202c",  # PDF (Pop Directional Formatting)
        "\u202d": r"\u202d",  # LRO (Left-to-Right Override)
        "\u202e": r"\u202e",  # RLO (Right-to-Left Override) - most dangerous
        # Line/paragraph separators
        "\u2028": r"\u2028",  # Line Separator
        "\u2029": r"\u2029",  # Paragraph Separator
        # Bidirectional isolates
        "\u2066": r"\u2066",  # LRI (Left-to-Right Isolate)
        "\u2067": r"\u2067",  # RLI (Right-to-Left Isolate)
        "\u2068": r"\u2068",  # FSI (First Strong Isolate)
        "\u2069": r"\u2069",  # PDI (Pop Directional Isolate)
    }
    for char, escaped in bidi_chars.items():
        text = text.replace(char, escaped)

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1f and char not in ("\n", "\r", "\t")) or 0x7f <= code <= 0x9f:
            result.append(f"\\x{code:02x}")
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
