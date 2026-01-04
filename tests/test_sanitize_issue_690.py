"""Test cases for Issue #690 - Format string attack prevention."""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringIssue690:
    """Tests for verify that sanitize_string prevents format string attacks.

    The issue reports that sanitize_string preserves backslash (\) and curly
    braces ({, }), which could be dangerous if the sanitized data is used in
    f-strings or .format() method calls, potentially leading to format string
    attacks.

    These characters should be removed to prevent such attacks.
    """

    def test_removes_backslash(self):
        """Test that backslashes are removed to prevent format string attacks."""
        # Backslash can be used in format strings for escaping
        input_str = "Test\\nString"
        result = sanitize_string(input_str)
        assert '\\' not in result, "Backslash should be removed to prevent format string attacks"

    def test_removes_curly_braces(self):
        """Test that curly braces are removed to prevent format string attacks."""
        # Curly braces are used in f-strings and .format()
        input_str = "Test {variable} String"
        result = sanitize_string(input_str)
        assert '{' not in result, "Opening curly brace should be removed"
        assert '}' not in result, "Closing curly brace should be removed"

    def test_format_string_attack_attempt(self):
        """Test that format string attack attempts are neutralized."""
        # Attempt to use format string syntax
        input_str = "{user.__class__}"
        result = sanitize_string(input_str)
        assert '{' not in result, "Format string attack should be prevented"
        assert '}' not in result, "Format string attack should be prevented"
        assert '__class__' not in result, "Dangerous attributes should be neutralized"

    def test_f_string_like_syntax(self):
        """Test that f-string-like syntax is neutralized."""
        # Simulate f-string injection attempt
        input_str = "{config.secret_key}"
        result = sanitize_string(input_str)
        assert '{' not in result, "F-string injection should be prevented"
        assert '}' not in result, "F-string injection should be prevented"

    def test_backslash_escape_sequences(self):
        """Test that backslash escape sequences are removed."""
        # Various escape sequences that could be dangerous
        input_str = "Test\\n\\t\\r\\x00"
        result = sanitize_string(input_str)
        assert '\\' not in result, "Backslash escape sequences should be removed"

    def test_preserves_other_safe_content(self):
        """Test that other safe content is still preserved."""
        # Regular content without dangerous characters should work
        input_str = "Regular Todo Title with numbers 123"
        result = sanitize_string(input_str)
        assert result == "Regular Todo Title with numbers 123"

    def test_still_removes_shell_operators(self):
        """Test that shell operators are still removed."""
        input_str = "Test; echo hacked"
        result = sanitize_string(input_str)
        assert ';' not in result, "Shell operators should still be removed"
