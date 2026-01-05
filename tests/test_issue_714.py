"""Tests for Issue #714 - Regex escape character validation.

Issue #714 reports that the regex escape character in dangerous_chars is problematic.
The current code has: dangerous_chars = r'\-;|&`$()<>{}'

In a character class [], the hyphen should be at the start or end to avoid being
interpreted as a range. The current implementation has it at the start, which is
correct. However, the issue suggests that the backslash might not work as intended.

This test verifies that:
1. Hyphens are properly removed from input
2. The regex doesn't create unintended ranges
3. Other dangerous characters are properly removed
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue714:
    """Test suite for Issue #714 - Regex escape character handling."""

    def test_hyphen_is_removed(self):
        """Test that hyphens are properly removed from input."""
        # Test single hyphen
        assert sanitize_string("test-with-hyphen") == "testwithhyphen"
        # Test multiple hyphens
        assert sanitize_string("a-b-c-d") == "abcd"

    def test_dangerous_chars_are_removed(self):
        """Test that all dangerous characters are removed."""
        # Test semicolon
        assert sanitize_string("test;value") == "testvalue"
        # Test pipe
        assert sanitize_string("test|value") == "testvalue"
        # Test ampersand
        assert sanitize_string("test&value") == "testvalue"
        # Test backtick
        assert sanitize_string("test`value") == "testvalue"
        # Test dollar sign
        assert sanitize_string("test$value") == "testvalue"
        # Test parentheses
        assert sanitize_string("test(value)") == "testvalue"
        # Test angle brackets
        assert sanitize_string("test<value>") == "testvalue"
        # Test curly braces
        assert sanitize_string("test{value}") == "testvalue"

    def test_combined_dangerous_chars(self):
        """Test combination of dangerous characters."""
        input_str = "test-with;danger|chars&like`this$one(and)<another>{final}"
        expected = "testwithdangercharslikethisoneandanotherfinal"
        assert sanitize_string(input_str) == expected

    def test_safe_characters_preserved(self):
        """Test that safe characters are preserved."""
        # Quotes should be preserved
        assert sanitize_string('test"quote\'') == 'test"quote\''
        # Brackets should be preserved
        assert sanitize_string("test[bracket]") == "test[bracket]"
        # Backslash should be preserved (Issue #705)
        assert sanitize_string("test\\backslash") == "test\\backslash"
        # Percentage should be preserved
        assert sanitize_string("test%percent") == "test%percent"

    def test_regex_no_unintended_ranges(self):
        """Test that the regex doesn't create unintended character ranges.

        This is the main concern from Issue #714 - if the hyphen escape doesn't
        work properly, it might create unintended ranges like ';' to '|' which
        would remove many unintended characters.
        """
        # Test characters that might be in an unintended range between ';' and '|'
        # ASCII: ';' = 59, '<' = 60, '=' = 61, '>' = 62, '?' = 63, '@' = 64, 'A' = 65, '|' = 124
        test_chars = ";<=?>@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`{|"

        # Only the explicitly listed dangerous chars should be removed
        # If there's an unintended range, many more characters would be removed
        result = sanitize_string(test_chars)

        # Expected result: only dangerous chars removed (;|&`$()<>{}), others preserved
        # Note: backslash \ is preserved per Issue #705
        expected = "<=>@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"

        assert result == expected, (
            f"Regex may have created unintended range.\n"
            f"Input: {repr(test_chars)}\n"
            f"Expected: {repr(expected)}\n"
            f"Got: {repr(result)}"
        )

    def test_empty_and_none_input(self):
        """Test edge cases."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""
