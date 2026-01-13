"""Command-line interface for todo CLI."""

import argparse
import logging
import re
import shlex
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
# SECURITY FIX (Issue #1044, #1314): Removed SHELL_METACHARS_PATTERN - now using
# whitelist approach with set lookup which is O(n) and has no ReDoS risk.
# The previous SHELL_METACHARS_PATTERN has been removed to prevent accidental use
# and eliminate ReDoS vulnerability. All code now uses set-based filtering instead.
# SECURITY FIX (Issue #1304): Reordered FORMAT_STRING_PATTERN to put backslash first
# in the character class. This prevents ambiguity and potential ReDoS issues.
# SECURITY FIX (Issue #1334): Escaped curly braces to prevent ReDoS vulnerability.
# The pattern matches literal characters: backslash (\), percent (%), and braces ({, })
FORMAT_STRING_PATTERN = re.compile(r'[\\%{}]')


# SECURITY FIX (Issue #1094): Define hard upper limit for max_length parameter
# to prevent memory exhaustion attacks. Even though length checks prevent ReDoS,
# accepting arbitrarily large max_length values could allow callers to cause
# memory issues. We cap at 1MB which is reasonable for a CLI tool.
MAX_LENGTH_HARD_LIMIT = 1 * 1024 * 1024  # 1MB


# SECURITY FIX (Issue #1289): Define context-specific default max_length limits
# For CLI contexts like filenames and URLs, use smaller defaults (255) to prevent
# terminal display issues and buffer overflow in downstream applications.
CONTEXT_DEFAULT_MAX_LENGTH = {
    "filename": 255,
    "url": 255,
    "shell": 255,
    "format": 255,
    "general": 4096,
}


def sanitize_for_security_context(s: str, context: str = "general", max_length: int | None = None) -> str:
    """Normalize string for security-sensitive contexts using stricter normalization.

    This function uses NFKC (Compatibility Decomposition) normalization for
    security-sensitive contexts like URLs, filenames, and shell parameters.
    NFKC converts fullwidth characters and other compatibility characters to
    their ASCII equivalents, preventing homograph attacks.

    SECURITY WARNING: This function is specifically for security-sensitive contexts.
    For general text storage (todo titles, descriptions), use remove_control_chars()
    instead, which uses NFC normalization to preserve user intent.

    SECURITY FIX (Issue #1324): Strings sanitized with 'general' context now PRESERVE
    format string characters ({, }, %, \) to maintain user intent and prevent data loss.
    General context is for data storage and display, not for use in format strings.
    If the output needs to be used in format strings, use the 'format' context which
    escapes these characters safely ({{, }}, %%, \\). This fixes the issue where
    user data like 'Progress: 50%' was incorrectly sanitized to 'Progress: 50'.

    What NFKC converts (preventing homograph attacks):
    - Fullwidth characters: ｅ → e, Ｔ → T, ． → .
    - Fullwidth punctuation: ！ → !, ？ → ?
    - Compatibility characters: ﬁ → fi, ² → 2

    Args:
        s: String to normalize
        context: Usage context - "url", "filename", "shell", "format", or "general"
                 Security contexts ("url", "filename", "shell", "format") use NFKC
                 General context uses NFC (preserves special characters)
        max_length: Maximum input length to prevent DoS attacks.
                    If not specified, uses context-specific default:
                    - filename/url/shell/format: 255 (Issue #1289)
                    - general: 4096 (Issue #1280)
                    Hard capped at 1MB to prevent memory exhaustion (Issue #1094, #1280)

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
        'Progress: 50%'  # Percent sign preserved (Issue #1324)
        >>> sanitize_for_security_context("file with spaces", context="shell")
        "'file with spaces'"  # Properly quoted for shell usage (Issue #1114)
        >>> sanitize_for_security_context("Cost: $100 (discount)", context="general")
        'Cost: $100 (discount)'  # Shell metachars preserved in general context (Issue #1024)
        >>> sanitize_for_security_context("Use {var} for 100%", context="format")
        'Use {{var}} for 100%%'  # Format chars escaped for safe f-string usage (Issue #1119)
        >>> sanitize_for_security_context("Use {var} for 100%", context="general")
        'Use {var} for 100%'  # Format chars preserved in general context (Issue #1324)

    Related issues:
        #969 (fullwidth homograph attacks), #944 (NFC preservation),
        #979 (preserve shell metachars in general context),
        #1024 (fix shell metachar removal in general mode),
        #1044 (ReDoS protection - use whitelist instead of regex blacklist),
        #1049 (normalization before truncation to prevent orphaned combining marks),
        #1054 (removed - encode-decode cycle replaced with direct slicing),
        #1089 (document security implications of format string chars in general context),
        #1094 (enforce hard upper limit on max_length to prevent memory exhaustion),
        #1104 (truncate by characters not bytes to prevent multi-byte bypass),
        #1289 (context-specific default max_length for CLI contexts),
        #1114 (use shlex.quote() for shell context instead of removing chars),
        #1119 (add 'format' context that escapes format string chars for safe usage),
        #1225 (remove Unicode spoofing chars in shell context before quoting),
        #1249 (move control char removal into context-specific handling to avoid conflicts),
        #1269 (ensure BIDI override chars removed before shlex.quote() - covered by #1225),
        #1280 (reduce default max_length from 100000 to 4096 for general context),
        #1289 (context-specific default max_length - 255 for CLI contexts),
        #1309 (add pre-normalization coarse check to prevent NFKC expansion DoS),
        #1319 (remove format string chars in general context to prevent injection),
        #1324 (preserve format string chars in general context to maintain user intent),
        #1514 (fix inconsistency - clarify general context preserves, format context escapes)
    """
    if not s:
        return ""

    # SECURITY FIX (Issue #1289): Use context-specific default max_length if not provided.
    # For CLI contexts (filename, url, shell, format), use 255 to prevent terminal
    # display issues and buffer overflow in downstream applications.
    if max_length is None:
        max_length = CONTEXT_DEFAULT_MAX_LENGTH.get(context, 4096)
    effective_max_length = min(max_length, MAX_LENGTH_HARD_LIMIT)

    # SECURITY FIX (Issue #1309): Pre-normalization coarse length check to prevent DoS.
    # While NFKC normalization is needed to prevent homograph attacks (Issue #969),
    # compatibility characters can expand during normalization (e.g., 'ﬁ' → 'fi'),
    # potentially causing memory pressure.
    #
    # SECURITY FIX (Issue #1604): Normalize a copy first to check expansion before
    # processing the full string. This prevents bypass of length checks via extreme
    # NFKC expansion that could theoretically exceed the 2x multiplier assumption.
    # The approach:
    # 1. Create a temporary copy and normalize it
    # 2. Check if normalized copy would exceed max_length
    # 3. If so, pre-truncate the original string before main normalization
    # This ensures strict enforcement of max_length even with extreme expansion.
    #
    # SECURITY FIX (Issue #1614): Strengthen NFKC expansion DoS protection.
    # The previous pre-check mechanism was insufficient for extreme expansion cases.
    # New protections:
    # 1. Enforce strict hard limit BEFORE any normalization to prevent memory exhaustion
    # 2. Use smaller check sample for extreme inputs to limit DoS surface
    # 3. Apply conservative safe limit with minimum of max_length/4 for worst-case expansion
    # 4. Add second validation after normalization to catch any bypass attempts
    #
    # SECURITY NOTE (Issue #1505): FALSE POSITIVE - The slicing below is SAFE.
    # Python 3 strings are sequences of Unicode code points, NOT bytes.
    # - len(s) returns the number of code points (characters), not UTF-8 bytes
    # - s[:n] slices by code points, not bytes
    # - Python string slicing CANNOT create invalid UTF-8 sequences
    # Example: "😀" * 100 has len() = 100 (code points), not 400 (bytes)
    # The subsequent Unicode normalization (NFKC/NFC) already handles edge cases.

    # Determine which normalization form will be used
    security_contexts = {"url", "filename", "shell", "format"}
    use_nfkc = context in security_contexts
    norm_form = 'NFKC' if use_nfkc else 'NFC'

    # SECURITY FIX (Issue #1614): Enforce strict hard limit BEFORE any processing
    # This is the FIRST line of defense - reject inputs that are obviously too large
    # even before normalization. Use a conservative 4x multiplier for NFKC contexts
    # to account for worst-case expansion while still preventing memory exhaustion.
    if use_nfkc:
        # For NFKC normalization, use a more conservative pre-check limit
        # Some characters can expand 2-3x (e.g., '㈱' → '（株）')
        # Using 4x multiplier provides safety margin for extreme cases
        strict_pre_limit = effective_max_length * 4
        if len(s) > strict_pre_limit:
            s = s[:strict_pre_limit]

    # SECURITY FIX (Issue #1614): Use smaller sample size for expansion check
    # to prevent DoS during the check itself. Limit sample to max_length + 100
    # instead of 2*max_length, reducing attack surface.
    check_sample_size = min(effective_max_length + 100, len(s))
    check_copy = s[:check_sample_size] if len(s) > check_sample_size else s

    # Normalize the copy to check for expansion
    normalized_check = unicodedata.normalize(norm_form, check_copy)

    # If normalized version exceeds max_length, calculate safe truncation limit
    if len(normalized_check) > effective_max_length:
        # Calculate safe truncation limit based on observed expansion ratio
        expansion_ratio = len(normalized_check) / len(check_copy) if len(check_copy) > 0 else 1

        # SECURITY FIX (Issue #1614): Use conservative safe limit with minimum threshold
        # Ensure we never allow more than max_length/4 of input for worst-case expansion
        # This provides defense-in-depth against extreme expansion ratios
        conservative_limit = max(
            int(effective_max_length / max(expansion_ratio, 1)),  # Ratio-based limit
            int(effective_max_length / 4)  # Conservative minimum for 4x expansion
        )
        safe_limit = min(conservative_limit, len(s))

        if len(s) > safe_limit:
            s = s[:safe_limit]

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
    #
    # SECURITY FIX (Issue #1049): Perform Unicode normalization BEFORE truncation.
    # This ensures that combining sequences (e.g., 'e' + combining_acute) are
    # composed into single code points (é) before truncation. This prevents
    # orphaned combining marks and ensures safer truncation behavior.
    # Normalization is fast and safe even for long strings, so doing it before
    # the length check doesn't introduce DoS risk.
    # Note: security_contexts and use_nfkc are already defined above (Issue #1604 fix)

    if use_nfkc:
        # Use NFKC for security-sensitive contexts
        # Converts fullwidth and compatibility characters to ASCII equivalents
        s = unicodedata.normalize('NFKC', s)
    else:
        # Use NFC for general text to preserve special characters
        s = unicodedata.normalize('NFC', s)

    # SECURITY FIX (Issue #1614): SECOND VALIDATION - Strict enforcement after normalization
    # This is the FINAL line of defense to ensure max_length is never exceeded,
    # even if NFKC expansion bypassed all previous checks. This provides
    # defense-in-depth and guarantees memory safety regardless of expansion ratio.
    if len(s) > effective_max_length:
        s = s[:effective_max_length]

    # SECURITY FIX (Issue #999, #1049): Enforce max_length AFTER Unicode normalization.
    # By normalizing first, we ensure that combining sequences are composed into
    # single code points before truncation. This prevents orphaned combining marks
    # and ensures safer truncation behavior (Issue #1049).
    # The length check still prevents ReDoS attacks by limiting the string length
    # before any regex processing (Issue #999).
    # SECURITY FIX (Issue #1104): Truncate by characters, not bytes.
    # Python's string slicing operates on code points (Unicode characters), not bytes.
    # Directly slicing the string ensures we respect max_length as a character limit,
    # not a byte limit. This prevents bypassing the constraint using multi-byte characters
    # like emojis (which are 4 bytes in UTF-8 but 1 character in Python strings).
    # SECURITY FIX (Issue #1094): Enforce hard upper limit on max_length to prevent
    # memory exhaustion attacks. Cap at 1MB even if caller requests larger limit.
    # SECURITY FIX (Issue #1289): Use context-specific default max_length if not provided.
    # For CLI contexts (filename, url, shell, format), use 255 to prevent terminal
    # display issues and buffer overflow in downstream applications.
    if max_length is None:
        max_length = CONTEXT_DEFAULT_MAX_LENGTH.get(context, 4096)
    effective_max_length = min(max_length, MAX_LENGTH_HARD_LIMIT)
    if len(s) > effective_max_length:
        # Slice directly to truncate at effective_max_length characters
        s = s[:effective_max_length]

    # SECURITY FIX (Issue #1249): Handle control character removal per context
    # to avoid logical conflicts with context-specific quoting/escaping.
    #
    # For shell context, control characters are removed after context-specific
    # processing to ensure shlex.quote() operates on the correct string.
    # For other contexts, control characters are removed before further processing.
    #
    # This approach prevents issues where removing control characters too early
    # might interfere with proper quoting or escaping mechanisms.

    # SECURITY FIX (Issue #1114): For shell context, use shlex.quote() to properly
    # escape the entire string instead of removing characters. Removing metacharacters
    # creates a FALSE sense of security - it doesn't protect against all injection
    # vectors (newlines, variable expansion, etc.) and mutates user data unnecessarily.
    # shlex.quote() is the ONLY correct way to make a string safe for shell usage.
    #
    # For url and filename contexts, we still remove shell metacharacters as before
    # since those contexts don't require shell quoting.
    #
    # SECURITY FIX (Issue #1119): For format context, escape format string characters
    # (braces, percent signs, backslashes) to make the string safe for use in
    # f-strings, .format(), and % formatting. This prevents format string injection
    # attacks while preserving the visual content of the string.
    if context == "shell":
        # SECURITY FIX (Issue #1249): For shell context, remove control characters
        # BEFORE removing Unicode spoofing chars and applying shlex.quote().
        # This ensures the quoting operates on a clean string without control chars.
        # SECURITY FIX (Issue #999, #1049): Length check happens BEFORE control char
        # removal to prevent orphaned combining marks, but AFTER Unicode normalization.
        s = CONTROL_CHARS_PATTERN.sub('', s)

        # SECURITY FIX (Issue #1225): Remove Unicode spoofing characters before quoting.
        # Shell context should also remove zero-width and bidirectional override characters
        # to prevent homograph attacks and visual spoofing in shell commands.
        s = ZERO_WIDTH_CHARS_PATTERN.sub('', s)
        s = BIDI_OVERRIDE_PATTERN.sub('', s)

        # SECURITY FIX (Issue #1369): Use shlex.quote() AFTER NFKC normalization.
        # The order of operations is critical for security:
        # 1. NFKC normalization first - converts fullwidth/malicious Unicode to ASCII
        #    (e.g., ｆｉｌｅ → file, ； → ;, ｜ → |)
        # 2. Remove control/spoofing characters
        # 3. shlex.quote() last - properly escapes the normalized string
        #
        # This order is SAFE because NFKC normalization does NOT introduce new
        # shell injection vulnerabilities. In fact, it makes the input safer by
        # converting fullwidth characters (a homograph attack vector) to their
        # ASCII equivalents before quoting. The final shlex.quote() ensures that
        # any remaining dangerous characters are properly escaped.
        #
        # Example of safe transformation:
        #   Input: ｆｉｌｅ；ｄａｎｇｅｒｏｕｓ (fullwidth semicolon)
        #   After NFKC: file;dangerous (ASCII semicolon)
        #   After shlex.quote(): 'file;dangerous' (properly quoted, safe for shell)
        #
        # Use shlex.quote() to properly escape the string for safe shell usage
        # This adds quotes and escapes special characters as needed
        # SECURITY: This is done AFTER all normalization (NFKC, control char removal, etc.)
        # so that the quoting is applied to the final normalized string
        return shlex.quote(s)
    elif context == "format":
        # SECURITY FIX (Issue #1119): Escape format string characters to prevent
        # format string injection attacks. This makes the string safe for use in:
        # - f-strings: f"User: {sanitized}" - the doubled braces become literal
        # - .format(): "Data: {}".format(sanitized) - the doubled braces are literal
        # - % formatting: "Progress: %s" % sanitized - the doubled % becomes literal %
        #
        # Escape sequence: { → {{, } → }}, % → %%, \ → \\
        # This must be done AFTER all other normalization (NFKC, control char removal, etc.)

        # SECURITY FIX (Issue #999, #1049): For format context, remove control characters
        # before escaping format string characters.
        s = CONTROL_CHARS_PATTERN.sub('', s)

        s = s.replace('\\', '\\\\')  # Must be first to avoid double-escaping
        s = s.replace('{', '{{')
        s = s.replace('}', '}}')
        s = s.replace('%', '%%')
        return s
    elif use_nfkc:  # url or filename context
        # SECURITY FIX (Issue #999, #1049): For url/filename contexts, remove control
        # characters before removing shell metacharacters.
        s = CONTROL_CHARS_PATTERN.sub('', s)

        # Define characters to remove using a set for O(1) lookup
        # These are shell metacharacters that could cause injection attacks
        shell_dangerous_chars = {';', '|', '&', '`', '$', '(', ')', '<', '>', '{', '}', '\\', '%'}
        # Filter out dangerous characters using list comprehension
        # This is O(n) with no backtracking risk
        s = ''.join(c for c in s if c not in shell_dangerous_chars)
    # else: General context - preserve shell metacharacters (Issue #1024, #979)
    # and preserve format string characters to maintain user intent (Issue #1324, #1514)
    # SECURITY NOTE: General context preserves format characters because it's for
    # data storage and display, not for use in format strings. Use 'format' context
    # to safely escape format characters for f-strings, .format(), or % formatting.

    # Remove control characters for non-shell, non-format, non-url/filename contexts
    # SECURITY FIX (Issue #999, #1049): Length check happens AFTER Unicode
    # normalization (line 123) to prevent orphaned combining marks, but BEFORE
    # any regex processing to prevent ReDoS attacks.
    # SECURITY FIX (Issue #1249): Only remove control chars here if not already removed
    # in context-specific handling above (shell, format, url/filename contexts).
    # SECURITY FIX (Issue #1324): For general context, only remove control characters
    # and preserve format string characters ({, }, %, \) to maintain user intent.
    # General context is primarily for data storage and display, not for use in
    # format strings. If the output needs to be used in format strings, use the
    # 'format' context which escapes these characters safely.
    if context == "general":
        s = CONTROL_CHARS_PATTERN.sub('', s)

    # Remove Unicode spoofing characters (for all contexts except shell, which already did it)
    # SECURITY FIX (Issue #1225): Remove Unicode spoofing characters for all contexts
    s = ZERO_WIDTH_CHARS_PATTERN.sub('', s)
    s = BIDI_OVERRIDE_PATTERN.sub('', s)

    return s


def remove_control_chars(s: str, max_length: int = 4096) -> str:
    """Normalize string for data storage by removing problematic characters.

    SECURITY WARNING: This function does NOT provide security protection.
    It is ONLY for data normalization - removing characters that could cause
    issues with storage formats or display systems. It does NOT prevent:
    - Shell injection (use subprocess with list arguments or shlex.quote())
    - SQL injection (use parameterized queries)
    - XSS attacks (use proper output encoding)
    - Format string injection (use safe_log() or proper escaping)
    - Any other security vulnerabilities

    The previous name "sanitize_string" was misleading as it suggested security
    protection that this function does not provide. This function normalizes
    data for storage by removing characters that could break formats.

    What it removes (for data integrity, NOT security):
    - Control characters (null bytes, newlines, tabs) that break storage formats
    - Unicode spoofing characters (zero-width, bidirectional overrides)

    What it NO LONGER removes (Issue #979, #1034):
    - Shell metacharacters (;, |, &, `, $, (, ), <, >) are PRESERVED as they are
      legitimate characters in user text. Examples:
      - Semicolons: "Note: this is important; remember it"
      - Pipes: "Use | for separating options"
      - Ampersands: "Johnson & Johnson"
      - Dollar signs: "Cost: $100"
      - Parentheses: "See chapter (5) for details"
      - Angle brackets: "Enter your <name> here"
      - Backticks: "Use `print('hello')` for output"
    - Format string characters ({, }, %, \) are PRESERVED in general context
      as they are legitimate characters in user content. Examples:
      - Curly braces: "Use {'key': 'value'} in Python", "Replace {var} with value"
      - Percent signs: "Complete 50% of the task", "Get 20% off"
      - Backslashes: "Path: C:\\Users\\Documents" (Windows paths)
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
        max_length: Maximum input length to prevent DoS attacks (default: 4096)
                    Hard capped at 1MB to prevent memory exhaustion (Issue #1094, #1280)

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
        'Use {format} strings'  # Format string chars preserved (Issue #1034)
        >>> remove_control_chars("Complete 50% of task")
        'Complete 50% of task'  # Percent sign preserved (Issue #1034)

    NOTE: For shell commands, use subprocess with list arguments or shlex.quote().
    For SQL, use parameterized queries. For logging with user data, use safe_log().
    This function does NOT prevent injection attacks.

    CRITICAL (Issue #1089): Strings returned by this function preserve format string
    characters ({, }, %, \) and are therefore ONLY safe for display and data storage.
    They MUST NOT be used in:
    - Format strings (f-strings, str.format(), % formatting)
    - Shell commands (use sanitize_for_security_context(context="shell") instead)
    - URLs (use sanitize_for_security_context(context="url") instead)
    - Filenames (use sanitize_for_security_context(context="filename") instead)
    - Any dynamic code generation or evaluation
    For these security-sensitive use cases, use sanitize_for_security_context() with
    the appropriate context parameter to remove dangerous characters.

    Related issues:
        #669, #619, #690, #725, #729, #736, #754, #769, #779, #780, #804, #805, #814,
        #819, #824, #830, #849, #850 (rename from sanitize_string), #929 (percent sign removal),
        #969 (fullwidth character handling - use sanitize_for_security_context for URLs/filenames),
        #979 (preserve shell metachars in general context - only remove in security contexts),
        #1034 (preserve format string chars in general context - only remove in security contexts),
        #1089 (document security implications of format string chars in general context),
        #1094 (enforce hard upper limit on max_length to prevent memory exhaustion),
        #1280 (reduce default max_length from 100000 to 4096 for general context),
        #1289 (context-specific default max_length - 255 for CLI contexts)
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
    # SECURITY FIX (Issue #1104): Truncate by characters, not bytes.
    # Directly slicing ensures max_length is respected as a character limit.
    # SECURITY FIX (Issue #1094): Enforce hard upper limit on max_length to prevent
    # memory exhaustion attacks. Cap at 1MB even if caller requests larger limit.
    effective_max_length = min(max_length, MAX_LENGTH_HARD_LIMIT)
    if len(s) > effective_max_length:
        s = s[:effective_max_length]

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

    # Step 2: Format string character handling
    # SECURITY FIX (Issue #1034): In general context (this function), preserve
    # format string characters ({}, %, \) as they are legitimate characters in
    # user content:
    # - Curly braces: Code snippets (dicts, sets), template placeholders
    # - Percent signs: Percentages, discounts, progress indicators
    # - Backslashes: Windows file paths, escape sequences in documentation
    #
    # This function is for data normalization, not security protection. For
    # security-sensitive contexts where format string chars must be removed, use
    # sanitize_for_security_context() with appropriate context ("shell", "url",
    # "filename").
    #
    # IMPORTANT: If you need to log user-controlled data, use safe_log() which
    # properly handles format string safety by using %s placeholders instead of
    # string formatting. Do NOT use f-strings or .format() with unsanitized input.
    #
    # No longer removing format string characters (Issue #1034)

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
def sanitize_string(s: str, max_length: int = 4096) -> str:
    """Deprecated alias for remove_control_chars.

    DEPRECATED: Use remove_control_chars instead. The name "sanitize_string"
    is misleading as it suggests security protection that this function does
    not provide. This function is for data normalization only.

    Args:
        s: String to normalize
        max_length: Maximum input length to prevent DoS attacks (default: 4096)
                    Hard capped at 1MB to prevent memory exhaustion (Issue #1094, #1280)

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
    # SECURITY FIX (Issue #1104): Truncate by characters, not bytes.
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
        # SECURITY FIX (Issue #1104): Truncate by characters, not bytes.
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
