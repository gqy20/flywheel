"""Test for Issue #1119 - Add 'format' context for safe format string usage.

Issue #1119 highlights that the 'general' context preserves format string characters
({, }, %, \) which makes it unsafe for use in format strings. This test verifies
that a new 'format' context properly escapes these characters to allow safe use
in format strings (f-strings, .format(), or % formatting).

The fix adds a 'format' context that escapes format string characters:
- Doubles braces: { → {{, } → }}
- Escapes percent signs: % → %%
- Escapes backslashes: \ -> \\
"""

import pytest

from flywheel.cli import sanitize_for_security_context


class TestIssue1119:
    """Test Issue #1119 - Add 'format' context for safe format string usage."""

    def test_format_context_escapes_curly_braces(self):
        """Format context should escape curly braces by doubling them."""
        # Single opening brace
        assert sanitize_for_security_context("Use {format}", context="format") == "Use {{format}}"

        # Single closing brace
        assert sanitize_for_security_context("item}", context="format") == "item}}"

        # Multiple braces
        assert sanitize_for_security_context("{key}", context="format") == "{{key}}"

        # Text with braces
        assert sanitize_for_security_context("Replace {var} with value", context="format") == "Replace {{var}} with value"

    def test_format_context_escapes_percent_signs(self):
        """Format context should escape percent signs by doubling them."""
        # Single percent
        assert sanitize_for_security_context("50%", context="format") == "50%%"

        # Multiple percents
        assert sanitize_for_security_context("100% complete", context="format") == "100%% complete"

        # Percent in middle
        assert sanitize_for_security_context("Progress: 50% done", context="format") == "Progress: 50%% done"

    def test_format_context_escapes_backslashes(self):
        """Format context should escape backslashes by doubling them."""
        # Single backslash
        assert sanitize_for_security_context("C:\\Users", context="format") == "C:\\\\Users"

        # Multiple backslashes
        assert sanitize_for_security_context("\\path\\to\\file", context="format") == "\\\\path\\\\to\\\\file"

    def test_format_context_escapes_combinations(self):
        """Format context should escape combinations of special characters."""
        # All special characters together
        assert sanitize_for_security_context("{path}% complete\\done", context="format") == "{{path}}%% complete\\\\done"

        # Complex example
        input_str = "Use {var} to get 100% done on C:\\path"
        expected = "Use {{var}} to get 100%% done on C:\\\\path"
        assert sanitize_for_security_context(input_str, context="format") == expected

    def test_format_context_preserves_safe_characters(self):
        """Format context should preserve non-dangerous characters."""
        # Normal text should be unchanged
        assert sanitize_for_security_context("Hello World", context="format") == "Hello World"

        # Alphanumeric and most punctuation preserved
        assert sanitize_for_security_context("Cost: $100 (discount)", context="format") == "Cost: $100 (discount)"

        # Shell metachars should be preserved in format context (we only escape format chars)
        assert sanitize_for_security_context("Command & more", context="format") == "Command & more"

    def test_format_context_safety_in_fstrings(self):
        """Verify that format context makes strings safe for f-string usage."""
        # Get a sanitized string that originally had format characters
        user_input = sanitize_for_security_context("{malicious}", context="format")

        # This should be safe to use in an f-string without injection
        # The doubled braces will be interpreted literally, not as format placeholders
        result = f"User entered: {user_input}"
        assert result == "User entered: {{malicious}}"

    def test_format_context_safety_in_format_method(self):
        """Verify that format context makes strings safe for .format() usage."""
        user_input = sanitize_for_security_context("{value}", context="format")

        # This should be safe - the doubled braces are literal
        result = "Data: {}".format(user_input)
        assert result == "Data: {{value}}"

    def test_format_context_safety_in_percent_formatting(self):
        """Verify that format context makes strings safe for % formatting."""
        user_input = sanitize_for_security_context("50%", context="format")

        # This should be safe - the doubled % becomes literal %
        result = "Progress: %s" % user_input
        assert result == "Progress: 50%%"

    def test_general_context_preserves_format_chars(self):
        """General context now removes format characters for security (Issue #1319)."""
        # This test verifies the security fix - format chars are removed in general context
        assert sanitize_for_security_context("{format}", context="general") == "format"
        assert sanitize_for_security_context("50%", context="general") == "50"
        assert sanitize_for_security_context("C:\\path", context="general") == "C:path"

    def test_format_context_vs_general_context(self):
        """Compare format context with general context after security fix (Issue #1319)."""
        input_str = "Use {var} for 100% on C:\\path"

        # General removes format characters (security fix)
        general_result = sanitize_for_security_context(input_str, context="general")
        assert general_result == "Use var for 100 on C:path"

        # Format escapes them (for literal display in format strings)
        format_result = sanitize_for_security_context(input_str, context="format")
        assert format_result == "Use {{var}} for 100%% on C:\\\\path"

        # They should be different - both safe but different approaches
        assert general_result != format_result
        # Both are safe for format strings, just different representations

    def test_format_context_with_empty_string(self):
        """Format context should handle empty strings."""
        assert sanitize_for_security_context("", context="format") == ""

    def test_format_context_with_unicode(self):
        """Format context should handle Unicode characters properly."""
        # Unicode should be preserved (NFC normalization applies)
        input_str = "Unicode: café {var} 50%"
        # After NFC normalization, the format chars should be escaped
        result = sanitize_for_security_context(input_str, context="format")
        assert "{{var}}" in result
        assert "50%%" in result
