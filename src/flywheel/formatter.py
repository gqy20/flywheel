"""Output formatter for todo data."""

from __future__ import annotations

import re

from .todo import Todo

# Control characters to sanitize: C0 controls except space (0x20) and DEL (0x7F)
# Includes \n, \r, \t, \x00-\x1F, \x7F, and ANSI escape sequences (\x1b)
_CONTROL_CHARS_PATTERN = re.compile(
    r"[\x00-\x1F\x7F]"
)


def _sanitize_text(text: str) -> str:
    """Remove control characters from text to prevent terminal injection.

    Removes ASCII control characters (0x00-0x1F, 0x7F) that could be used to:
    - Inject fake output lines (\\n, \\r)
    - Manipulate terminal display (ANSI escape sequences starting with \\x1b)
    - Break table formatting (\\t)

    Args:
        text: The input text that may contain control characters.

    Returns:
        Sanitized text with all control characters removed.
    """
    return _CONTROL_CHARS_PATTERN.sub("", text)


class TodoFormatter:
    """Render todos in simple text tables."""

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(str(todo.text))
        return f"[{status}] {todo.id:>3} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
