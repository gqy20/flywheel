"""Tests for sanitize_string function - Issue #639

This test file verifies that sanitize_string properly filters out:
- Newline characters (\n, \x0A)
- Tab characters (\t, \x09)
- All other ASCII control characters (\x00-\x1F, \x7F)

Issue: https://github.com/anthropics/flywheel/issues/639
"""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringIssue639:
    """Test that sanitize_string removes all ASCII control characters including \n and \t."""

    def test_newline_removed(self):
        """Test that newline characters are removed."""
        # Single newline
        assert sanitize_string("hello\nworld") == "helloworld"
        # Multiple newlines
        assert sanitize_string("line1\nline2\nline3") == "line1line2line3"
        # Newline at start
        assert sanitize_string("\nstart") == "start"
        # Newline at end
        assert sanitize_string("end\n") == "end"
        # Only newlines
        assert sanitize_string("\n\n\n") == ""

    def test_tab_removed(self):
        """Test that tab characters are removed."""
        # Single tab
        assert sanitize_string("hello\tworld") == "helloworld"
        # Multiple tabs
        assert sanitize_string("col1\tcol2\tcol3") == "col1col2col3"
        # Tab at start
        assert sanitize_string("\tstart") == "start"
        # Tab at end
        assert sanitize_string("end\t") == "end"
        # Only tabs
        assert sanitize_string("\t\t\t") == ""

    def test_mixed_newline_and_tab(self):
        """Test that both newline and tab characters are removed."""
        assert sanitize_string("line1\n\tline2") == "line1line2"
        assert sanitize_string("\n\t\n\t") == ""

    def test_all_ascii_control_chars_removed(self):
        """Test that all ASCII control characters (0x00-0x1F, 0x7F) are removed."""
        # Null byte
        assert sanitize_string("hello\x00world") == "helloworld"
        # Start of heading
        assert sanitize_string("hello\x01world") == "helloworld"
        # Various control characters
        assert sanitize_string("test\x02\x03\x04\x05string") == "teststring"
        # DEL character (0x7F)
        assert sanitize_string("hello\x7Fworld") == "helloworld"

    def test_normal_chars_preserved(self):
        """Test that normal characters are preserved."""
        assert sanitize_string("normal text") == "normal text"
        assert sanitize_string("Hello, World!") == "Hello, World!"
        assert sanitize_string("test-123") == "test-123"

    def test_empty_and_none(self):
        """Test edge cases."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""
