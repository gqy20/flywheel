"""Output formatter for todo data."""

from __future__ import annotations

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
    def format_todo(todo: Todo, id_width: int = 3) -> str:
        """Format a single todo item.

        Args:
            todo: The todo item to format.
            id_width: Minimum width for the ID field for alignment.
                      Defaults to 3 for backward compatibility with single calls.

        Returns:
            Formatted string representation of the todo.
        """
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)
        return f"[{status}] {todo.id:>{id_width}} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        """Format a list of todos with aligned ID columns.

        Calculates the required ID width based on the largest ID to ensure
        all todo text starts at the same column regardless of ID magnitude.

        Args:
            todos: List of todo items to format.

        Returns:
            Formatted string with one todo per line, or "No todos yet." for empty list.
        """
        if not todos:
            return "No todos yet."
        # Calculate dynamic width: at least 3 chars, or wider if IDs are larger
        max_id = max(todo.id for todo in todos)
        id_width = max(3, len(str(max_id)))
        return "\n".join(cls.format_todo(todo, id_width) for todo in todos)
