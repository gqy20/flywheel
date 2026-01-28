"""Test for Issue #815 - Inconsistent sanitization logic allows newline characters

This test verifies that newline and carriage return characters are properly handled.
The fix ensures that control characters (newlines, tabs, etc.) are replaced with
spaces instead of being removed completely, which prevents word concatenation
(e.g., 'Hello\nWorld' → 'Hello World' instead of 'HelloWorld').
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue815NewlineHandling:
    """Test suite for Issue #815 - Newline character handling in sanitization."""

    def test_newline_character_replaced_with_space(self):
        """Test that newline characters are replaced with spaces to preserve word separation."""
        result = sanitize_string("Hello\nWorld")
        # After fix: newlines are replaced with spaces
        assert result == "Hello World"

    def test_carriage_return_replaced_with_space(self):
        """Test that carriage return characters are replaced with spaces."""
        result = sanitize_string("Hello\rWorld")
        assert result == "Hello World"

    def test_crlf_replaced_with_spaces(self):
        """Test that CRLF (Windows line endings) are replaced with spaces."""
        result = sanitize_string("Hello\r\nWorld")
        # Both CR and LF become spaces
        assert result == "Hello  World"

    def test_newline_with_spaces(self):
        """Test that newlines with spaces are handled correctly."""
        result = sanitize_string("Hello\n World")
        assert result == "Hello  World"

    def test_multiple_newlines(self):
        """Test multiple consecutive newline characters."""
        result = sanitize_string("Line1\n\n\nLine2")
        # Multiple newlines become multiple spaces
        assert result == "Line1   Line2"

    def test_newline_in_middle_of_sentence(self):
        """Test newline character in the middle of a sentence."""
        result = sanitize_string("This is a test\nof the system")
        assert result == "This is a test of the system"

    def test_tab_character_replaced_with_space(self):
        """Test that tab characters are replaced with spaces."""
        # Tab is \x09, also in the \x00-\x1F range
        result = sanitize_string("Hello\tWorld")
        assert result == "Hello World"

    def test_control_characters_range(self):
        """Test various control characters in the \x00-\x1F range."""
        # Test a few control characters
        result = sanitize_string("Start\x01\x02\x03End")
        # Control chars become spaces
        assert result == "Start   End"

    def test_valid_input_unchanged(self):
        """Test that valid input without control characters remains unchanged."""
        result = sanitize_string("Normal text with spaces and punctuation!")
        assert result == "Normal text with spaces and punctuation!"

    def test_newline_at_start(self):
        """Test newline at the start of string."""
        result = sanitize_string("\nStart here")
        assert result == " Start here"

    def test_newline_at_end(self):
        """Test newline at the end of string."""
        result = sanitize_string("End here\n")
        assert result == "End here "

    def test_shell_metachars_still_removed(self):
        """Test that shell metacharacters are still removed correctly."""
        # Ensure shell metacharacter removal still works
        result = sanitize_string("Hello; World | Test & More")
        assert result == "Hello World  Test  More"

    def test_mixed_control_chars_and_metachars(self):
        """Test handling of both control characters and shell metacharacters."""
        result = sanitize_string("Hello\nWorld; Test\tHere")
        # Control chars become spaces, metachars are removed
        assert result == "Hello World Test Here"
