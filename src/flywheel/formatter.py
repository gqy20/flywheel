"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo

# Control characters to sanitize: ASCII 0-31 (except printable whitespace like space)
# and ANSI escape character (0x1b / ESC)
_CONTROL_CHARS_TO_REMOVE = {
    "\x00",  # Null byte
    "\x01",  # Start of heading
    "\x02",  # Start of text
    "\x03",  # End of text
    "\x04",  # End of transmission
    "\x05",  # Enquiry
    "\x06",  # Acknowledge
    "\x07",  # Bell
    "\x08",  # Backspace
    "\x0b",  # Vertical tab
    "\x0c",  # Form feed
    "\x0e",  # Shift out
    "\x0f",  # Shift in
    "\x10",  # Data link escape
    "\x11",  # Device control 1
    "\x12",  # Device control 2
    "\x13",  # Device control 3
    "\x14",  # Device control 4
    "\x15",  # Negative acknowledge
    "\x16",  # Synchronous idle
    "\x17",  # End of transmission block
    "\x18",  # Cancel
    "\x19",  # End of medium
    "\x1a",  # Substitute
    "\x1b",  # Escape (ANSI escape sequences)
    "\x1c",  # File separator
    "\x1d",  # Group separator
    "\x1e",  # Record separator
    "\x1f",  # Unit separator
    "\x7f",  # Delete
}


def _sanitize_text(text: str) -> str:
    """Remove control characters that could cause terminal injection.

    Removes newline, carriage return, tab, null byte, ANSI escape sequences,
    and other non-printable control characters.
    """
    # Remove all control characters except space (0x20)
    # We translate each control char to None (delete it)
    translation_table = str.maketrans("", "", "".join(_CONTROL_CHARS_TO_REMOVE))
    # Also explicitly remove \n, \r, \t (newline, carriage return, tab)
    text = text.translate(translation_table)
    text = text.replace("\n", "").replace("\r", "").replace("\t", "")
    return text


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
