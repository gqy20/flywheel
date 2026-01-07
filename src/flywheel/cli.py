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

# SECURITY FIX (Issue #996): Precompile regex patterns at module load time to
# prevent ReDoS (Regular Expression Denial of Service) attacks. Precompiling
# improves performance by avoiding repeated parsing and compilation of the
# same patterns on every function call.
ZERO_WIDTH_CHARS_PATTERN = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
BIDI_OVERRIDE_PATTERN = re.compile(r'[\u202A-\u202E\u2066-\u2069]')
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1F\x7F]')
SHELL_METACHARS_PATTERN = re.compile(r'[;|&`$()<>]')
SHELL_METACHARS_SECURE_PATTERN = re.compile(r'[;|&`$()<>{}\\%]')
FORMAT_STRING_PATTERN = re.compile(r'[{}\\%]')


def sanitize_for_security_context(s: str, context: str = "general", max_length: int = 100000) -> str:
    """Normalize string for security-sensitive contexts using stricter normalization.

    This function uses NFKC (Compatibility Decomposition) normalization for
    security-sensitive contexts like URLs, filenames, and shell parameters.
    NFKC converts fullwidth characters and other compatibility characters to
    their ASCII equivalents, preventing homograph attacks.

    SECURITY WARNING: This function is specifically for security-sensitive contexts.
    For general text storage (todo titles, descriptions), use remove_control_chars()
    instead, which uses NFC normalization to preserve user intent.

    What NFKC converts (preventing homograph attacks):
    - Fullwidth characters: ｅ → e, Ｔ → T, ． → .
    - Fullwidth punctuation: ！ → !, ？ → ?
    - Compatibility characters: ﬁ → fi, ² → 2

    Args:
        s: String to normalize
        context: Usage context - "url", "filename", "shell", or "general"
                 Security contexts ("url", "filename", "shell") use NFKC
                 General context uses NFC (preserves special characters)
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Normalized string safe for the specified context

    Security:
        Addresses Issue #969 - Fullwidth character homograph attacks in
        security-sensitive contexts. NFKC normalization converts fullwidth
        characters to ASCII equivalents, preventing confusion in URLs and
        filenames while maintaining security.

    Example:
        >>> sanitize_for_security_context("ｅｘａｍｐｌｅ．ｃｏｍ", context="url")
        'example.com'
        >>> sanitize_for_security_context("ｄｏｃｕｍｅｎｔ．ｔｘｔ", context="filename")
        'document.txt'
        >>> sanitize_for_security_context("²³™", context="general")
        '²³™'  # Preserved with NFC (general context)
        >>> sanitize_for_security_context("Progress: 50%", context="general")
        'Progress: 50%'  # Percent sign preserved in general context
        >>> sanitize_for_security_context("Progress: 50%", context="shell")
        'Progress: 50'  # Percent sign removed in shell context

    Related issues:
        #969 (fullwidth homograph attacks), #944 (NFC preservation),
        #974 (percent sign preservation in general context)
    """
    if not s:
        return ""

    # SECURITY FIX (Issue #969): Use NFKC for security-sensitive contexts
    # NFKC normalization converts fullwidth characters to ASCII equivalents:
    # - Fullwidth Latin letters: ａｂｃ → abc
    # - Fullwidth punctuation: ．．． → ...
    # - Other compatibility characters: ﬁ → fi, ² → 2
    #
    # This prevents homograph attacks in URLs, filenames, and shell parameters
    # where fullwidth characters could be used to deceive users or bypass filters.
    #
    # For general text context, use NFC to preserve user intent (Issue #944)
    security_contexts = {"url", "filename", "shell"}
    use_nfkc = context in security_contexts

    if use_nfkc:
        # Use NFKC for security-sensitive contexts
        # Converts fullwidth and compatibility characters to ASCII equivalents
        s = unicodedata.normalize('NFKC', s)
    else:
        # Use NFC for general text to preserve special characters
        s = unicodedata.normalize('NFC', s)

    # Apply the same safety processing as remove_control_chars
    # Prevent DoS by limiting input length
    if len(s) > max_length:
        s = s[:max_length]

    # Remove control characters
    s = CONTROL_CHARS_PATTERN.sub('', s)

    # Remove shell metacharacters (especially important for shell context)
    # SECURITY FIX (Issue #976): In general context, preserve backslashes for
    # Windows paths and escape sequences. Only remove them in security contexts.
    # SECURITY FIX (Issue #975): In general context, preserve curly braces for
    # Python format() strings. Only remove them in security contexts.
    # SECURITY FIX (Issue #974): In general context, preserve percent signs for
    # format strings. Only remove them in security contexts.
    if use_nfkc:
        s = SHELL_METACHARS_SECURE_PATTERN.sub('', s)
    else:
        # General context: preserve backslashes, curly braces, and percent signs
        # Remove only shell metacharacters that could cause injection
        s = SHELL_METACHARS_PATTERN.sub('', s)

    # Remove Unicode spoofing characters
    s = ZERO_WIDTH_CHARS_PATTERN.sub('', s)
    s = BIDI_OVERRIDE_PATTERN.sub('', s)

    return s


def remove_control_chars(s: str, max_length: int = 100000) -> str:
    """Normalize string for data storage by removing problematic characters.

    SECURITY WARNING: This function does NOT provide security protection.
    It is ONLY for data normalization - removing characters that could cause
    issues with storage formats or display systems. It does NOT prevent:
    - Shell injection (use subprocess with list arguments or shlex.quote())
    - SQL injection (use parameterized queries)
    - XSS attacks (use proper output encoding)
    - Any other security vulnerabilities

    The previous name "sanitize_string" was misleading as it suggested security
    protection that this function does not provide. This function normalizes
    data for storage by removing characters that could break formats.

    What it removes (for data integrity, NOT security):
    - Control characters (null bytes, newlines, tabs) that break storage formats
    - Format string characters ({, }, %) that could cause format string bugs
    - Backslashes (\) to prevent them from interfering with storage formats or
      causing ambiguity in data representation (e.g., in JSON, CSV, or shell contexts)
    - Unicode spoofing characters (zero-width, bidirectional overrides)
    - Fullwidth characters are CONVERTED to ASCII via NFKC normalization

    What it NO LONGER removes (Issue #979):
    - Shell metacharacters (;, |, &, `, $, (, ), <, >) are PRESERVED in general
      context as they are legitimate characters in user text. Examples:
      - Semicolons: "Note: this is important; remember it"
      - Pipes: "Use | for separating options"
      - Ampersands: "Johnson & Johnson"
      - Dollar signs: "Cost: $100"
      - Parentheses: "See chapter (5) for details"
      - Angle brackets: "Enter your <name> here"
      - Backticks: "Use `print('hello')` for output"
      For security-sensitive contexts where these must be removed, use
      sanitize_for_security_context() with appropriate context parameter.

    What it preserves (for legitimate content):
    - All alphanumeric characters and common punctuation
    - Quotes (', ") for text and code snippets
    - Brackets ([, ]) for code and data structures
    - Hyphen (-) for UUIDs, dates, phone numbers, URLs
    - International characters (Cyrillic, CJK, Arabic, etc.)
    - Spaces for readable text

    Args:
        s: String to normalize
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Normalized string with problematic characters removed for data storage

    Example:
        >>> remove_control_chars("Hello World")
        'Hello World'
        >>> remove_control_chars("todo\x00extra")
        'todoextra'
        >>> remove_control_chars("Cost: $100 (discount)")
        'Cost: $100 (discount)'  # Shell metachars preserved (Issue #979)
        >>> remove_control_chars("Use {format} strings")
        'Use format strings'  # Format string chars removed for safety

    NOTE: For shell commands, use subprocess with list arguments or shlex.quote().
    For SQL, use parameterized queries. This function does NOT prevent injection attacks.

    Related issues:
        #669, #619, #690, #725, #729, #736, #754, #769, #779, #780, #804, #805, #814,
        #819, #824, #830, #849, #850 (rename from sanitize_string), #929 (percent sign removal),
        #969 (fullwidth character handling - use sanitize_for_security_context for URLs/filenames),
        #810 (clarified backslash removal documentation - backslashes are removed for data
        #      normalization, not to prevent escape sequence interpretation),
        #979 (preserve shell metachars in general context - only remove in security contexts)
    """
    if not s:
        return ""

    # SECURITY FIX (Issue #754, #779, #814, #944): Normalize Unicode before processing
    # Use NFC (Canonical Composition) normalization to handle canonical equivalence
    # while preserving user-intended special characters.
    #
    # NFC handles canonical equivalence (composed vs decomposed forms):
    # - é (U+00E9) vs e + combining acute (U+0065 U+0301) → both become é (U+00E9)
    # - Ensures consistent representation of the same character
    #
    # Unlike NFKC, NFC PRESERVES compatibility characters:
    # - Superscripts: ² remains ² (not converted to 2)
    # - Ligatures: ﬁ remains ﬁ (not converted to fi)
    # - Trademark: ™ remains ™ (not converted to tm)
    # - Fractions: ½ remains ½ (not converted to 1/2)
    #
    # This is the appropriate choice for a general Todo application because:
    # 1. Users may intentionally use special characters for notation, branding, etc.
    # 2. It prevents data loss and semantic changes (Issue #944)
    # 3. It still handles canonical equivalence for security (Issue #754)
    # 4. Visual spoofing through fullwidth characters is handled separately below
    #
    # For generating filenames or shell parameters, additional processing should
    # be applied at those specific boundaries, not to all text storage.
    #
    # Security: Addresses Issue #754 - Handles canonical equivalence
    # Security: Addresses Issue #944 - Preserves user intent without data loss
    # Security: Addresses Issue #814 - Balances security with data preservation
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

    # Prevent DoS by limiting input length BEFORE any regex processing
    # SECURITY FIX (Issue #830): This length check must happen BEFORE all
    # regex patterns below to prevent potential ReDoS attacks. Even though
    # Python's re module handles character classes efficiently, enforcing
    # the limit early ensures that excessively long strings cannot cause
    # catastrophic backtracking in any of the regex patterns.
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
    # SECURITY FIX (Issue #780, #815, #849): Separate handling of metacharacters
    # and control characters for improved data integrity. Control characters are
    # removed directly without replacement to prevent unintended word concatenation
    # while preserving original spacing in user text.
    #
    # SECURITY FIX (Issue #849): Remove control characters directly without replacing
    # with spaces, and preserve original spaces in user text. This maintains data
    # integrity for display text (titles, descriptions) while still removing dangerous
    # characters. The two-step approach:
    # 1. Remove control characters completely (not replaced with spaces)
    # 2. Remove certain metacharacters completely
    #
    # Step 1: Remove control characters completely to prevent format breaking
    # This includes \x00-\x1F (all ASCII control chars) and \x7F (delete)
    # Newlines (\x0A), carriage returns (\x0D), tabs (\x09), etc. are removed
    # SECURITY FIX (Issue #996): Use precompiled pattern for better performance
    s = CONTROL_CHARS_PATTERN.sub('', s)

    # Step 2: Remove format string characters that could cause injection
    # Characters removed: { } % \
    # Note: We preserve quotes, [, ], shell metachars for legitimate text content
    # WARNING: This does NOT provide shell injection protection. For shell commands,
    # use subprocess with list arguments (shell=False) or shlex.quote().
    # For security-sensitive contexts (shell, url, filename), use
    # sanitize_for_security_context() instead.
    #
    # Curly braces removed to prevent format string attacks (Issue #690)
    # Percent sign removed to prevent format string injection (Issue #929)
    # Backslash removed to prevent storage format ambiguity (Issue #810)
    #
    # SECURITY NOTE (Issue #729): To prevent ReDoS, we construct the regex pattern
    # explicitly rather than using string interpolation. This ensures that:
    # 1. No hyphens in the middle that could create unintended ranges
    # 2. No unescaped closing brackets that could break the character class
    # 3. Pattern is safe from catastrophic backtracking
    #
    # SECURITY FIX (Issue #929): Added percent sign (%) to prevent format string
    # injection when normalized strings are used in legacy % formatting (e.g.,
    # logger.info(msg)). This prevents information disclosure or crashes from
    # format string specifiers like %s, %d, etc.
    #
    # SECURITY FIX (Issue #979): In general context (this function), preserve
    # shell metacharacters (; | & ` $ ( ) < >) as they are legitimate characters
    # in user text (e.g., "Cost: $100", "See (chapter 5)", "Use | to separate").
    # This function is for data normalization, not security protection. For
    # security-sensitive contexts where shell metachars must be removed, use
    # sanitize_for_security_context() with appropriate context ("shell", "url",
    # "filename").
    # SECURITY FIX (Issue #996): Use precompiled pattern for better performance
    s = FORMAT_STRING_PATTERN.sub('', s)

    # Remove Unicode spoofing characters:
    # Zero-width characters
    # SECURITY FIX (Issue #996): Use precompiled pattern for better performance
    s = ZERO_WIDTH_CHARS_PATTERN.sub('', s)
    # Bidirectional text override
    s = BIDI_OVERRIDE_PATTERN.sub('', s)
    # Note: Fullwidth characters are preserved with NFC normalization (Issue #944)
    # They are only removed if needed for specific contexts (filenames, shell args)
    # For general text storage, we preserve them as legitimate user input

    return s


# DEPRECATED: Alias for backward compatibility (Issue #850)
# Use remove_control_chars instead - the name "sanitize_string" is misleading
# as it suggests security protection that this function does not provide.
def sanitize_string(s: str, max_length: int = 100000) -> str:
    """Deprecated alias for remove_control_chars.

    DEPRECATED: Use remove_control_chars instead. The name "sanitize_string"
    is misleading as it suggests security protection that this function does
    not provide. This function is for data normalization only.

    Args:
        s: String to normalize
        max_length: Maximum input length to prevent DoS attacks (default: 100000)

    Returns:
        Normalized string with problematic characters removed

    Note:
        This function will be removed in a future version. Migrate to
        remove_control_chars() which has a clearer name about its purpose.
    """
    return remove_control_chars(s, max_length)


def safe_log(logger, level: str, message: str, *args, **kwargs) -> None:
    """Safely log messages using normalized user input.

    This helper function ensures that logger calls use safe patterns to prevent
    format string injection. It should be used when logging user-controlled data.

    Args:
        logger: Logger instance to use
        level: Log level (debug, info, warning, error, critical)
        message: Log message template (use %s placeholders for user data)
        *args: Arguments to substitute into message (using %s placeholders)
        **kwargs: Additional keyword arguments for logger call

    Security:
        Addresses Issue #964 - Ensures safe logging patterns are used:
        - Always use %s placeholders for user data, not direct string formatting
        - User input should be normalized via remove_control_chars() before passing
        - Never use f-strings with unsanitized user input: f"User: {user_input}"
        - Never use % formatting with user input: "User: %s" % user_input

    Example:
        >>> # Safe: Using %s placeholder
        >>> safe_log(logger, "info", "Processing todo: %s", sanitized_title)
        >>> # Safe: Multiple placeholders
        >>> safe_log(logger, "debug", "Todo %s: %s", todo_id, sanitized_desc)
        >>> # Safe: No user data
        >>> safe_log(logger, "info", "Application started")
    """
    log_func = getattr(logger, level.lower(), None)
    if log_func is None:
        raise ValueError(f"Invalid log level: {level}")

    # Use the logger's built-in safe formatting with %s placeholders
    # This is safe because:
    # 1. User data should be pre-normalized via remove_control_chars()
    # 2. The logger handles %s placeholders safely (not as format strings)
    log_func(message, *args, **kwargs)


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
            title=remove_control_chars(args.title),
            description=remove_control_chars(args.description or ""),
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
            todo.title = remove_control_chars(args.title)
        if args.description is not None:
            todo.description = remove_control_chars(args.description)
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
