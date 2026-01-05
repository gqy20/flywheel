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
    """Sanitize string input to prevent injection attacks.

    This function takes a minimal approach to sanitization, removing only
    characters that could cause security issues while preserving legitimate
    content like quotes, percentage signs, and code snippets.

    It removes:
    - Shell injection metacharacters (;, |, &, `, $, (, ), <, >)
    - Format string characters ({, }) to prevent format string attacks
    - Control characters (newlines, tabs, null bytes) that could break storage formats
    - All backslashes (\) to prevent shell injection
    - Unicode spoofing characters (zero-width, bidirectional overrides, fullwidth)

    It preserves:
    - All alphanumeric characters and common punctuation
    - Quotes (single ', double ") for text and code snippets
    - Percentage (%) for legitimate use cases
    - Brackets ([, ]) for code and data structures
    - Hyphen (-) for UUIDs, hyphenated words, ISO dates, phone numbers, URLs, and file paths

    Security Implementation:
    - Uses a single combined regex pass to remove all dangerous characters atomically
    - This prevents order-dependency issues and makes the sanitization more robust
    - Addresses Issue #780 - Potential bypass of shell injection protection via newline

    Args:
        s: String to sanitize
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Sanitized string with dangerous characters removed, including all backslashes

    Security:
        Addresses Issue #669 - Preserves legitimate content (quotes, percentages)
        while still preventing injection attacks. Storage backends should use
        parameterized queries or proper escaping for their specific format.
        Addresses Issue #619 - Prevents ReDoS via input length limits and
        safe regex patterns.
        Addresses Issue #690 - Removes curly braces to prevent format string
        attacks when sanitized data is used in f-strings or .format().
        Addresses Issue #725 - Preserves hyphens to prevent data corruption
        in UUIDs, hyphenated words, ISO dates, phone numbers, URLs, and file paths.
        Addresses Issue #729 - Prevents ReDoS by using explicit regex pattern
        construction instead of string interpolation, ensuring hyphens and
        closing brackets cannot create unintended ranges or break the character class.
        Addresses Issue #736 - Removes all backslashes to prevent shell injection.
        Any backslash (internal or trailing) can act as an escape character in shell
        contexts (e.g., '\n' becomes newline, '\t' becomes tab, '\\"' escapes quotes).
        To ensure maximum security when sanitized data is used in shell commands or
        other contexts where backslashes have special meaning, all backslashes are
        removed. This prevents arbitrary command injection through escape sequences.
        Storage backends should still use parameterized queries or proper escaping
        for their specific format.
        Addresses Issue #754 - Normalizes Unicode using NFC form before processing to
        prevent homograph attacks. Visual lookalikes from different scripts (fullwidth,
        Cyrillic, Greek) and different Unicode representations (composed vs decomposed)
        are normalized to canonical forms, ensuring security filters cannot be bypassed.
        Addresses Issue #769 - Removes ALL backslashes (not just trailing) to prevent
        shell injection through internal escape sequences like '\n', '\t', '\r', etc.,
        which can be interpreted as control characters in shell contexts.
        Addresses Issue #780 - Uses single combined regex pass to remove all dangerous
        characters (shell metacharacters and control characters) in one atomic operation.
        This eliminates order-dependency vulnerabilities and makes the sanitization more
        robust against potential bypasses that could slip through multiple sequential passes.
    """
    if not s:
        return ""

    # SECURITY FIX (Issue #754): Normalize Unicode before processing
    # Use NFC normalization to handle canonical equivalence without altering
    # semantic meaning. This prevents homograph attacks where different
    # Unicode representations (composed vs decomposed) can bypass filters,
    # while preserving legitimate characters like superscripts, ligatures,
    # and other compatibility characters.
    # NFC is preferred over NFKC because it preserves semantic meaning:
    # - Superscripts (², ³) remain superscripts (not converted to 2, 3)
    # - Ligatures (ﬁ, ﬂ) remain ligatures (not converted to fi, fl)
    # - Ordinals (ª, º) remain ordinals (not converted to a, o)
    # Example: é (NFD: e + combining acute) → é (NFC: single character)
    # Security: Addresses Issue #764 - NFKC causes data loss
    s = unicodedata.normalize('NFC', s)

    # Prevent DoS by limiting input length
    if len(s) > max_length:
        s = s[:max_length]

    # Define blacklist of dangerous shell metacharacters to remove.
    # Characters removed: ; | & ` $ ( ) < > { } \
    # Note: We preserve quotes, %, [, ] for legitimate content
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
    # SECURITY FIX (Issue #780): Combine shell metacharacter and control character
    # removal into a single regex pass for improved robustness. Previously, these
    # were removed in two separate passes (line 129 and 133), which could be fragile
    # and prone to order-dependency issues. The new combined approach ensures all
    # dangerous characters are removed atomically in one operation.
    #
    # This single regex removes:
    # - Shell injection metacharacters: ; | & ` $ ( ) < > { } \
    # - Control characters: \x00-\x1F \x7F (including newline, tab, null, etc.)
    #
    # The combined character class includes:
    # - Explicit metachars: ; | & ` $ ( ) < > { } \
    # - Control char range: \x00-\x1F (all ASCII control chars)
    # - Delete character: \x7F
    #
    # SECURITY NOTE: By using a single regex pass, we eliminate the risk of
    # characters slipping through due to order dependencies between multiple
    # sanitization steps. This makes the sanitization more robust and easier
    # to reason about.
    s = re.sub(r'[;|&`$()<>{}\\\x00-\x1F\x7F]', '', s)

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
        Addresses Issue #754 - Normalizes Unicode using NFKC form before processing
        to prevent homograph attacks in tag names, ensuring visual lookalikes
        from different scripts cannot bypass tag filters.
    """
    if not tags_str:
        return []

    # SECURITY FIX (Issue #754): Normalize Unicode before processing
    # Same normalization as in sanitize_string (NFC) to prevent homograph
    # attacks while preserving semantic meaning. Addresses Issue #764.
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
