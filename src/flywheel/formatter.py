"""Output formatter for todo data."""

from __future__ import annotations

import textwrap

from .todo import Todo


def _sanitize_text(text: str) -> str:
    """Escape control characters to prevent terminal output manipulation.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations
    to prevent injection attacks via todo text.
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
    def format_todo(todo: Todo, width: int = 80) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)
        prefix = f"[{status}] {todo.id:>3} "

        if width <= len(prefix):
            # If width is too small, just return prefix + text (no wrapping)
            return prefix + safe_text

        available_width = width - len(prefix)

        if len(safe_text) <= available_width:
            return prefix + safe_text

        # Wrap the text at available_width and add indentation to continuation lines
        wrapped_lines = textwrap.wrap(safe_text, width=available_width)
        result = prefix + wrapped_lines[0]
        for line in wrapped_lines[1:]:
            result += "\n" + " " * len(prefix) + line
        return result

    @classmethod
    def format_list(cls, todos: list[Todo], width: int = 80) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo, width=width) for todo in todos)
