"""Command-line interface for todo CLI."""

import argparse
import logging
import re
import sys
from datetime import datetime

from flywheel.formatter import Formatter, FormatType
from flywheel.storage import Storage
from flywheel.todo import Priority, Status, Todo

logger = logging.getLogger(__name__)


def sanitize_string(s: str, max_length: int = 100000) -> str:
    """Sanitize string input to prevent injection attacks.

    This function removes dangerous characters that could be used for:
    - HTML/Script injection (removes <, >, quotes)
    - Shell injection (removes ;, |, &, `, $, (, ))
    - Command injection (removes newlines, tabs, null bytes)
    - Format string attacks (removes %)
    - Unicode spoofing (removes fullwidth characters, zero-width characters,
      control characters, bidirectional overrides)

    However, it preserves:
    - Alphanumeric characters (a-z, A-Z, 0-9)
    - Basic punctuation (period, comma, colon, exclamation, question mark)
    - Whitespace (spaces for readability)
    - Hyphens and underscores for compound words

    Args:
        s: String to sanitize
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Sanitized string with dangerous characters removed

    Security:
        Addresses Issue #609 - Ensures title and description fields are safe
        for storage backends that may render HTML or execute shell commands.
        Addresses Issue #619 - Prevents ReDoS via input length limits and
        safe regex patterns.
    """
    if not s:
        return ""

    # Prevent DoS by limiting input length
    if len(s) > max_length:
        s = s[:max_length]

    # Define blacklist of dangerous characters to remove.
    # Using a simple character class with explicit escaping to prevent ReDoS.
    # Characters removed: < > " ' ` $ & | ; ( ) [ ] { } \ %
    dangerous_chars = r'<>\"\'`$&|;()\[\]{}\\%'
    s = re.sub(f'[{dangerous_chars}]', '', s)

    # Remove all ASCII control characters (including newline and tab)
    s = re.sub(r'[\x00-\x1F\x7F]', '', s)

    # Remove Unicode spoofing characters:
    # Zero-width characters
    s = re.sub(r'[\u200B-\u200D\u2060\uFEFF]', '', s)
    # Bidirectional text override
    s = re.sub(r'[\u202A-\u202E\u2066-\u2069]', '', s)
    # Fullwidth characters (U+FF01-FF60) - convert or remove
    s = re.sub(r'[\uFF01-\uFF60]', '', s)

    return s


def sanitize_tags(tags_str, max_length=10000, max_tags=100):
    """Sanitize tag input to prevent injection attacks.

    This function uses a whitelist approach to only allow safe characters:
    - Alphanumeric characters (a-z, A-Z, 0-9)
    - Underscores (_)
    - Hyphens (-)

    This prevents:
    - Shell injection (metacharacters like ;, |, &, `, $, (), <, >)
    - JSON injection (quotes and other special characters)
    - Command injection (newlines, null bytes)
    - Unicode spoofing characters (fullwidth characters, zero-width characters,
      homoglyphs, control characters, bidirectional overrides, etc.)
    - ReDoS attacks (by limiting input length and number of tags)

    Args:
        tags_str: Comma-separated tag string from user input
        max_length: Maximum length of input string to prevent DoS (default: 10000)
        max_tags: Maximum number of tags to process (default: 100)

    Returns:
        List of sanitized tags containing only allowed characters

    Security:
        Addresses Issue #599 - Ensures tags are safe for storage backends
        including JSON files and potential SQL databases.
        Addresses Issue #604 - Uses whitelist approach to block Unicode
        spoofing characters and control characters.
        Addresses Issue #635 - Prevents ReDoS by limiting input length and
        tag count before processing.
    """
    if not tags_str:
        return []

    # Prevent DoS by limiting input length before processing
    if len(tags_str) > max_length:
        tags_str = tags_str[:max_length]

    # Split by comma
    raw_tags = tags_str.split(",")

    # Prevent DoS by limiting number of tags processed
    if len(raw_tags) > max_tags:
        raw_tags = raw_tags[:max_tags]

    sanitized_tags = []

    for tag in raw_tags:
        # Strip whitespace
        tag = tag.strip()

        # Use whitelist approach: only keep ASCII word characters ([a-zA-Z0-9_])
        # and hyphens. Using explicit ASCII range prevents Unicode spoofing.
        # This removes all dangerous characters including:
        # - Shell metacharacters
        # - Unicode spoofing characters
        # - Control characters
        # - Zero-width characters
        # - Bidirectional overrides
        # - Fullwidth characters
        # - Emoji and symbols
        tag = re.sub(r'[^a-zA-Z0-9_\-]', '', tag)

        # Only add non-empty tags after sanitization
        if tag:
            sanitized_tags.append(tag)

    return sanitized_tags


class CLI:
    """Todo CLI application."""

    def __init__(self):
        self.storage = Storage()

    def add(self, args: argparse.Namespace) -> None:
        """Add a new todo."""
        todo = Todo(
            id=None,  # Let storage.generate ID atomically
            title=sanitize_string(args.title),
            description=sanitize_string(args.description or ""),
            priority=Priority(args.priority) if args.priority else Priority.MEDIUM,
            due_date=sanitize_string(args.due_date) if args.due_date else None,
            tags=sanitize_tags(args.tags) if args.tags else [],
        )

        added_todo = self.storage.add(todo)
        print(f"✓ Added todo #{added_todo.id}: {added_todo.title}")

    def list(self, args: argparse.Namespace) -> None:
        """List todos."""
        status_filter = args.status

        if args.all:
            todos = self.storage.list()
        elif status_filter:
            todos = self.storage.list(status_filter)
        else:
            # By default, show only incomplete todos
            todos = [t for t in self.storage.list() if t.status != Status.DONE]

        # Sort by priority
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        todos.sort(key=lambda t: (priority_order.get(t.priority, 99), t.id))

        formatter = Formatter(FormatType(args.format) if args.format else FormatType.TABLE)
        print(formatter.format(todos))

    def complete(self, args: argparse.Namespace) -> None:
        """Mark a todo as complete."""
        todo = self.storage.get(args.id)
        if not todo:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

        todo.status = Status.DONE
        todo.completed_at = datetime.now().isoformat()
        self.storage.update(todo)
        print(f"✓ Completed todo #{args.id}: {todo.title}")

    def delete(self, args: argparse.Namespace) -> None:
        """Delete a todo."""
        if self.storage.delete(args.id):
            print(f"✓ Deleted todo #{args.id}")
        else:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

    def update(self, args: argparse.Namespace) -> None:
        """Update a todo."""
        todo = self.storage.get(args.id)
        if not todo:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

        if args.title:
            todo.title = sanitize_string(args.title)
        if args.description is not None:
            todo.description = sanitize_string(args.description)
        if args.status:
            todo.status = Status(args.status)
        if args.priority:
            todo.priority = Priority(args.priority)

        self.storage.update(todo)
        print(f"✓ Updated todo #{args.id}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Flywheel Todo CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new todo")
    add_parser.add_argument("title", help="Todo title")
    add_parser.add_argument("-d", "--description", help="Todo description")
    add_parser.add_argument("-p", "--priority", choices=["low", "medium", "high"])
    add_parser.add_argument("--due-date", help="Due date (ISO format)")
    add_parser.add_argument("-t", "--tags", help="Comma-separated tags")

    # List command
    list_parser = subparsers.add_parser("list", help="List todos")
    list_parser.add_argument("-a", "--all", action="store_true", help="Show all todos")
    list_parser.add_argument("-s", "--status", choices=["todo", "in_progress", "done"])
    list_parser.add_argument("-f", "--format", choices=["table", "json", "compact"])

    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Mark todo as complete")
    complete_parser.add_argument("id", type=int, help="Todo ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a todo")
    delete_parser.add_argument("id", type=int, help="Todo ID")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a todo")
    update_parser.add_argument("id", type=int, help="Todo ID")
    update_parser.add_argument("-t", "--title", help="New title")
    update_parser.add_argument("-d", "--description", help="New description")
    update_parser.add_argument("-s", "--status", choices=["todo", "in_progress", "done"])
    update_parser.add_argument("-p", "--priority", choices=["low", "medium", "high"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = CLI()
    command = getattr(cli, args.command)
    command(args)


if __name__ == "__main__":
    main()
