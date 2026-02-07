"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Sanitize text by escaping control characters.

    Replaces control characters (ASCII 0-31 except space) with their
    escape sequence representations to prevent terminal output manipulation.

    Args:
        text: The input text that may contain control characters

    Returns:
        Text with control characters escaped as \\xNN, \\n, \\r, \\t, etc.
    """
    # Map common control characters to readable escapes
    control_map = {
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\x0b": "\\v",  # vertical tab
        "\x0c": "\\f",  # form feed
    }

    result = []
    for char in text:
        if char in control_map:
            result.append(control_map[char])
        elif ord(char) < 32 or char == "\x7f":
            # Other control characters: use hex escape
            result.append(f"\\x{ord(char):02x}")
        else:
            result.append(char)
    return "".join(result)


class TodoFormatter:
    """Render todos in simple text tables."""

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        sanitized_text = _sanitize_text(todo.text)
        return f"[{status}] {todo.id:>3} {sanitized_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
