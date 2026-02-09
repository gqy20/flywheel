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
        """Format a single todo with optional text wrapping.

        Args:
            todo: The todo item to format.
            width: Maximum line width. Text longer than this will wrap.
                   Default is 80 for backward compatibility.

        Returns:
            Formatted todo string, possibly with multiple lines if text wraps.
        """
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)

        # Create the prefix: "[status] id "
        prefix = f"[{status}] {todo.id:>3} "

        # Calculate available width for text
        # Subtract prefix length and one space
        available_width = width - len(prefix)

        # If text fits in one line, return simple format
        if len(safe_text) <= available_width or available_width < 10:
            return f"{prefix}{safe_text}"

        # Text needs wrapping - use textwrap.fill() with proper indentation
        # First line has no extra indent (prefix provides it)
        # Subsequent lines are indented to align with prefix
        initial_indent = ""
        subsequent_indent = " " * len(prefix)

        wrapped = textwrap.fill(
            safe_text,
            width=available_width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=True,
            break_on_hyphens=False,
        )

        return f"{prefix}{wrapped}"

    @classmethod
    def format_list(cls, todos: list[Todo], width: int = 80) -> str:
        """Format a list of todos with optional text wrapping.

        Args:
            todos: List of todo items to format.
            width: Maximum line width for wrapping. Default is 80.

        Returns:
            Formatted multi-line string with all todos.
        """
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo, width=width) for todo in todos)
