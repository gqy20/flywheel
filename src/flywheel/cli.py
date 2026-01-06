"""Command-line interface for todo CLI."""

import argparse
import logging
import re
import string
import sys
import unicodedata
from datetime import datetime

from flywheel.formatter import Formatter, FormatType
from flywheel.storage import Storage
from flywheel.todo import Priority, Status, Todo

logger = logging.getLogger(__name__)


def sanitize_string(s: str, max_length: int = 100000) -> str:
    """Clean string input for data storage (NOT for shell command safety).

    WARNING: This function is NOT suitable for preventing shell injection.
    If you need to execute shell commands with user input, use Python's
    subprocess module with list arguments (shell=False) or shlex.quote().
    This function is only intended for basic data cleaning before storage.

    This function removes characters that could cause issues in data storage
    or display formats, while preserving legitimate content.

    It removes:
    - Shell metacharacters (;, |, &, `, $, (, ), <, >) that could interfere
      with various text formats or display systems
    - Format string characters ({, }) to prevent format string attacks
    - Control characters (newlines, tabs, null bytes) that could break storage formats
    - All backslashes (\) that could cause escape sequence issues
    - Unicode spoofing characters (zero-width, bidirectional overrides, fullwidth)

    It preserves:
    - All alphanumeric characters and common punctuation
    - Quotes (single ', double ") for text and code snippets
    - Percentage (%) for legitimate use cases
    - Brackets ([, ]) for code and data structures
    - Hyphen (-) for UUIDs, hyphenated words, ISO dates, phone numbers, URLs, and file paths
    - International characters (Cyrillic, CJK, Arabic, etc.) for legitimate multilingual content

    Args:
        s: String to sanitize
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Cleaned string with certain characters removed for data storage safety

    NOTE:
        This function preserves quotes and other special characters for legitimate
        text content. It does NOT provide shell injection protection. For shell
        command execution, always use subprocess with list arguments (shell=False)
        or proper quoting libraries like shlex.quote(). Storage backends should use
        parameterized queries or proper escaping for their specific format.

    Security:
        Addresses Issue #669 - Preserves legitimate content (quotes, percentages)
        for data storage. Shell safety should be handled by subprocess with list
        arguments, not by sanitization.
        Addresses Issue #619 - Prevents ReDoS via input length limits and
        safe regex patterns.
        Addresses Issue #690 - Removes curly braces to prevent format string
        attacks when sanitized data is used in f-strings or .format().
        Addresses Issue #725 - Preserves hyphens to prevent data corruption
        in UUIDs, hyphenated words, ISO dates, phone numbers, URLs, and file paths.
        Addresses Issue #729 - Prevents ReDoS by using explicit regex pattern
        construction instead of string interpolation.
        Addresses Issue #736 - Removes backslashes that could cause escape
        sequence issues in various contexts.
        Addresses Issue #754 - Normalizes Unicode using NFC form before processing.
        Addresses Issue #769 - Removes all backslashes to prevent escape sequence issues.
        Addresses Issue #780 - Uses separate passes for control characters and
        metacharacters to preserve word separation.
        Addresses Issue #804 - Preserves international characters for multilingual support.
        Addresses Issue #824 - Clarifies that this function is NOT suitable for
        shell injection prevention. Shell safety must be handled by using subprocess
        with list arguments (shell=False) or shlex.quote() when executing commands.
    """
    if not s:
        return ""

    # SECURITY FIX (Issue #754, #814): Normalize Unicode before processing
    # Use NFC (Canonical Composition) normalization to handle canonical equivalence
    # without causing data loss. NFC only combines characters (e.g., 'e + ´' → 'é')
    # and does NOT alter semantic meaning like NFKC does.
    #
    # NFKC (previous approach) caused irreversible data loss by converting:
    # - Superscripts: ² → 2, ³ → 3
    # - Ligatures: ﬁ → fi, ﬂ → fl
    # - Fullwidth: Ａ → A, ０ → 0
    #
    # NFC preserves user data while still handling canonical equivalence:
    # - é (NFD: e + combining acute) → é (single character)
    # - All compatibility characters are preserved as-is
    #
    # Security: Addresses Issue #814 - NFKC causes irreversible data loss
    # Security: Addresses Issue #754 - NFC handles canonical equivalence
    s = unicodedata.normalize('NFC', s)

    # SECURITY FIX (Issue #804): Preserve international characters for multilingual support.
    # Previous implementation restricted all input to Latin-script characters only to prevent
    # visual homograph attacks. However, this was too restrictive for general text input
    # like todo titles and descriptions, where users should be able to write in their
    # native languages (Cyrillic, CJK, Arabic, etc.).
    #
    # Visual homograph attack prevention should only be applied where necessary (e.g.,
    # when generating filenames or shell parameters), not to all text input. For general
    # text storage, we preserve international characters while still removing characters
    # that could interfere with data formats or display systems.

    # Prevent DoS by limiting input length
    if len(s) > max_length:
        s = s[:max_length]

    # Remove certain metacharacters that could interfere with data formats or display systems.
    # Characters removed: ; | & ` $ ( ) < > { } \
    # Note: We preserve quotes, %, [, ] for legitimate text content
    # WARNING: This does NOT provide shell injection protection. For shell commands,
    # use subprocess with list arguments (shell=False) or shlex.quote().
    # Curly braces removed to prevent format string attacks (Issue #690)
    # Hyphen preserved to prevent data corruption (Issue #725):
    # - UUIDs (550e8400-e29b-41d4-a716-446655440000)
    # - Hyphenated words (well-known, self-contained)
    # - ISO dates (2024-01-15)
    # - Phone numbers (1-800-555-0123)
    # - URLs and file paths
    #
    # SECURITY NOTE (Issue #729): To prevent ReDoS, we construct the regex pattern
    # explicitly rather than using string interpolation. This ensures that:
    # 1. No hyphens in the middle that could create unintended ranges
    # 2. No unescaped closing brackets that could break the character class
    # 3. Pattern is safe from catastrophic backtracking
    #
    # SECURITY FIX (Issue #780, #815): Separate handling of metacharacters
    # and control characters for improved data integrity. Previously, these were
    # removed in a single pass which could cause word concatenation issues when
    # newlines were removed (e.g., 'Hello\nWorld' → 'HelloWorld').
    #
    # SECURITY FIX (Issue #815): Replace control characters (newlines, tabs, etc.)
    # with spaces instead of removing them completely. This prevents word
    # concatenation and preserves data integrity. The two-step approach:
    # 1. Replace control characters with spaces
    # 2. Remove certain metacharacters completely
    #
    # Step 1: Replace control characters with spaces to preserve word separation
    # This includes \x00-\x1F (all ASCII control chars) and \x7F (delete)
    # Newlines (\x0A), carriage returns (\x0D), tabs (\x09), etc. become spaces
    control_chars_pattern = r'[\x00-\x1F\x7F]'
    s = re.sub(control_chars_pattern, ' ', s)

    # Step 2: Remove certain metacharacters that could interfere with data formats
    # Characters removed: ; | & ` $ ( ) < > { } \
    # Note: We preserve quotes, %, [, ] for legitimate text content
    # WARNING: This does NOT provide shell injection protection. For shell commands,
    # use subprocess with list arguments (shell=False) or shlex.quote().
    # Curly braces removed to prevent format string attacks (Issue #690)
    # Hyphen preserved to prevent data corruption (Issue #725):
    # - UUIDs (550e8400-e29b-41d4-a716-446655440000)
    # - Hyphenated words (well-known, self-contained)
    # - ISO dates (2024-01-15)
    # - Phone numbers (1-800-555-0123)
    # - URLs and file paths
    #
    # SECURITY NOTE (Issue #729): To prevent ReDoS, we construct the regex pattern
    # explicitly rather than using string interpolation. This ensures that:
    # 1. No hyphens in the middle that could create unintended ranges
    # 2. No unescaped closing brackets that could break the character class
    # 3. Pattern is safe from catastrophic backtracking
    shell_metachars_pattern = r'[;|&`$()<>{}\\]'
    s = re.sub(shell_metachars_pattern, '', s)

    # Remove Unicode spoofing characters:
    # Zero-width characters
    s = re.sub(r'[\u200B-\u200D\u2060\uFEFF]', '', s)
    # Bidirectional text override
    s = re.sub(r'[\u202A-\u202E\u2066-\u2069]', '', s)
    # Fullwidth characters (U+FF01-FF60) - convert or remove
    s = re.sub(r'[\uFF01-\uFF60]', '', s)

    return s


def validate_date(date_str: str) -> str:
    """Validate and normalize a date string to ISO format.

    This function uses datetime.fromisoformat to validate that the date string
    conforms to ISO 8601 format standards. This prevents invalid dates from being
    stored in the system.

    Args:
        date_str: Date string to validate

    Returns:
        The validated date string in ISO format

    Raises:
        ValueError: If the date string is not a valid ISO 8601 date

    Security:
        Addresses Issue #715 - Validates date format using datetime.fromisoformat
        to ensure only valid ISO dates are accepted, preventing format errors and
        potential injection through malformed date strings.
    """
    try:
        # Attempt to parse the date string - this will raise ValueError if invalid
        parsed_date = datetime.fromisoformat(date_str)
        # Return the normalized ISO format
        return parsed_date.isoformat()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Must be ISO 8601 format (e.g., '2024-01-15' or '2024-01-15T10:30:00')") from e


def sanitize_tags(tags_str, max_length=10000, max_tags=100, max_tag_length=100):
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
    - ReDoS attacks (by using non-regex approach instead of regex patterns)

    Args:
        tags_str: Comma-separated tag string from user input
        max_length: Maximum length of input string to prevent DoS (default: 10000)
        max_tags: Maximum number of tags to process (default: 100)
        max_tag_length: Maximum length of individual tags to prevent abuse (default: 100)

    Returns:
        List of sanitized tags containing only allowed characters and passing
        format validation (no leading/trailing/consecutive hyphens)

    Security:
        Addresses Issue #599 - Ensures tags are safe for storage backends
        including JSON files and potential SQL databases.
        Addresses Issue #604 - Uses whitelist approach to block Unicode
        spoofing characters and control characters.
        Addresses Issue #635 - Prevents ReDoS by limiting input length and
        tag count before processing.
        Addresses Issue #689 - Validates tag format to reject tags starting
        or ending with hyphens, or containing consecutive hyphens. This prevents
        formatting issues and logic errors where hyphen-prefixed tags could be
        confused with CLI flags or cause parsing problems.
        Addresses Issue #704 - Uses non-regex approach (all() + str.isalnum)
        to completely eliminate ReDoS risk from regex backtracking.
        Addresses Issue #735 - Places hyphen at the end of allowed_chars
        string to prevent it from creating unintended character ranges in
        regex character classes, eliminating potential ReDoS vulnerabilities.
        Addresses Issue #751 - Limits individual tag length to prevent abuse
        through extremely long tags that could cause storage or display issues.
        Addresses Issue #754 - Normalizes Unicode using NFC form before processing
        to prevent homograph attacks in tag names, ensuring visual lookalikes
        from different scripts cannot bypass tag filters.
        Addresses Issue #774 - Whitelist approach (ASCII only) already prevents
        visual homograph attacks from non-Latin scripts (Cyrillic, Greek, etc.)
        by only allowing ASCII alphanumeric characters, underscores, and hyphens.
    """
    if not tags_str:
        return []

    # SECURITY FIX (Issue #754, #814): Normalize Unicode before processing
    # Same normalization as in sanitize_string (NFC) to handle canonical
    # equivalence without causing data loss. Addresses Issue #814.
    tags_str = unicodedata.normalize('NFC', tags_str)

    # Prevent DoS by limiting input length before processing
    if len(tags_str) > max_length:
        tags_str = tags_str[:max_length]

    # Split by comma
    raw_tags = tags_str.split(",")

    # Prevent DoS by limiting number of tags processed
    if len(raw_tags) > max_tags:
        raw_tags = raw_tags[:max_tags]

    sanitized_tags = []

    # Define allowed characters: ASCII alphanumeric, underscore, hyphen
    # SECURITY FIX (Issue #735): Place hyphen at the end to prevent it from
    # creating a character range in regex character classes. When used in
    # patterns like [chars], a hyphen in the middle (e.g., '_-') creates a
    # range, which can cause ReDoS vulnerabilities. Placing it at the end
    # ensures it's treated as a literal hyphen character.
    allowed_chars = set(string.ascii_letters + string.digits + '_' + '-')

    for tag in raw_tags:
        # Strip whitespace
        tag = tag.strip()

        # Truncate tag if it exceeds max_tag_length to prevent abuse
        # This addresses Issue #751 - individual tag length limit
        if len(tag) > max_tag_length:
            tag = tag[:max_tag_length]

        # Use non-regex whitelist approach: only keep allowed characters
        # This completely eliminates ReDoS risk from regex backtracking
        # by using Python's built-in character checking methods
        sanitized = ''.join(c for c in tag if c in allowed_chars)

        # SECURITY FIX (Issue #689): Validate tag format to prevent:
        # - Tags starting with hyphens (could be confused with CLI flags)
        # - Tags ending with hyphens (formatting issues)
        # - Tags with consecutive hyphens (could cause parsing issues)
        # Only add tags that pass all validation checks
        if (sanitized and
            not sanitized.startswith('-') and
            not sanitized.endswith('-') and
            '--' not in sanitized):
            sanitized_tags.append(sanitized)

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
            due_date=validate_date(args.due_date) if args.due_date else None,
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
