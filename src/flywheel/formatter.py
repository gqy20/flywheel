"""Output formatter for todo data."""

from __future__ import annotations

from .todo import Todo


class TodoFormatter:
    """Render todos in simple text tables."""

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Escape control characters to prevent terminal injection.

        This neutralizes characters that could be used for:
        - Terminal control sequences (ANSI escapes)
        - Log injection (newlines, carriage returns)
        - String truncation (null bytes)
        - Output formatting corruption (tabs, backspace)

        Args:
            text: The input text to sanitize

        Returns:
            Text with control characters replaced by safe escape sequences
        """
        # Replace in order of most dangerous to least dangerous
        replacements = [
            ("\x00", "\\x00"),  # Null byte
            ("\x1b", "\\x1b"),  # Escape (ANSI sequences)
            ("\n", "\\n"),       # Newline
            ("\r", "\\r"),       # Carriage return
            ("\t", "\\t"),       # Tab
            ("\x08", "\\x08"),   # Backspace
            ("\x07", "\\x07"),   # Bell
            ("\x0b", "\\x0b"),   # Vertical tab
            ("\x0c", "\\x0c"),   # Form feed
        ]
        for char, replacement in replacements:
            text = text.replace(char, replacement)
        return text

    @staticmethod
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = TodoFormatter._sanitize_text(todo.text)
        return f"[{status}] {todo.id:>3} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
