"""Output formatter for todo data."""

from __future__ import annotations

import re

from .todo import Todo


def _sanitize_error_message(exc: Exception) -> str:
    """Sanitize exception messages to prevent sensitive path leakage.

    Removes full filesystem paths from error messages while preserving:
    - Filenames (basename only)
    - Error types and context
    - Line/column numbers for JSON errors

    This prevents information disclosure via error messages while keeping
    errors useful for debugging.

    Args:
        exc: The exception to sanitize

    Returns:
        A sanitized error message safe for user display
    """
    import os

    message = str(exc)

    # Special handling for storage.py path error format:
    # "Path error: '/part/path' exists as a file, not a directory. Cannot use '/full/path' as database path."
    # Both paths should be fully sanitized, not just the basename
    if "Path error:" in message and "exists as a file, not a directory" in message:
        # Replace all path-like strings with generic placeholders
        sanitized = re.sub(
            r"'/[^']+'",  # Match any single-quoted path
            lambda m: f"'<path>/{os.path.basename(m.group(0)[1:-1])}'",
            message,
        )
        return sanitized

    # Step 1: Replace all quoted paths (most common pattern)
    # Matches: '/path/to/file.ext' or "/path/to/file.ext" or '/any/path/to/thing'
    def replace_quoted_path(match: re.Match[str]) -> str:
        quote = match.group(1)
        path = match.group(2)
        # Get the last path component
        parts = path.rstrip("/").split("/")
        basename = parts[-1] if parts else "file"
        return f"{quote}<path>/{basename}{quote}"

    # Match quoted paths - any absolute path in quotes
    # This handles: '/absolute/path/file.json', "/absolute/path/file", etc.
    quoted_path_pattern = r"(['\"])(/[^'\"]+\.[^'\"]{1,10}|/[^'\"]+/[^'\"]+)['\"]"
    sanitized = re.sub(quoted_path_pattern, replace_quoted_path, message)

    # Step 2: Handle other error prefixes with paths
    def replace_prefixed_path(match: re.Match[str]) -> str:
        prefix = match.group(1)
        path = match.group(2)
        rest = match.group(3) if len(match.groups()) >= 3 else ""
        parts = path.rstrip("/").split("/")
        basename = parts[-1] if parts else "file"
        return f"{prefix}<path>/{basename}{rest}"

    # Matches: "Permission denied: '/path'" or "Invalid JSON in '/path'"
    error_prefix_pattern = r"(Permission denied|Invalid JSON in|Failed to create directory):\s+['\"]?(/[^\s'\"]+)['\"]?([:\s]*.*)"
    sanitized = re.sub(error_prefix_pattern, replace_prefixed_path, sanitized)

    # Step 3: Additional protection - remove usernames from paths
    # Strip usernames from paths like /home/username/ or /Users/username/
    sanitized = re.sub(r"/home/[^/]+/", "/home/<user>/", sanitized)
    sanitized = re.sub(r"/Users/[^/]+/", "/Users/<user>/", sanitized)

    # Step 4: Remove any remaining absolute paths with 3+ components
    # This catches patterns like /any/directory/that/has/multiple/parts
    long_path_pattern = r'/[\w_-]+/[\w_-]+/[\w_-]+[\w/._-]*'
    sanitized = re.sub(
        long_path_pattern,
        lambda m: f"<path>/{os.path.basename(m.group(0).rstrip('/'))}",
        sanitized,
    )

    return sanitized


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
    def format_todo(todo: Todo) -> str:
        status = "x" if todo.done else " "
        safe_text = _sanitize_text(todo.text)
        return f"[{status}] {todo.id:>3} {safe_text}"

    @classmethod
    def format_list(cls, todos: list[Todo]) -> str:
        if not todos:
            return "No todos yet."
        return "\n".join(cls.format_todo(todo) for todo in todos)
