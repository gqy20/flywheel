"""Test for issue #795 - Verify backslash removal in sanitize_string.

This test verifies that the sanitize_string function properly removes all backslashes
to prevent shell injection attacks, as documented in the function's docstring.
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue795:
    """Test suite for issue #795 - Backslash removal verification."""

    def test_backslash_at_end(self):
        """Test that trailing backslashes are removed."""
        # Single backslash at end
        assert sanitize_string("test\\") == "test"

        # Multiple backslashes at end
        assert sanitize_string("test\\\\\\") == "test"

    def test_backslash_at_start(self):
        """Test that leading backslashes are removed."""
        # Single backslash at start
        assert sanitize_string("\\test") == "test"

        # Multiple backslashes at start
        assert sanitize_string("\\\\\\test") == "test"

    def test_backslash_in_middle(self):
        """Test that internal backslashes are removed."""
        # Backslash in the middle
        assert sanitize_string("test\\ing") == "testing"

        # Multiple backslashes in the middle
        assert sanitize_string("test\\\\ing") == "testing"

    def test_backslash_escape_sequences(self):
        """Test that backslash escape sequences are removed."""
        # Newline escape sequence
        assert sanitize_string("test\\nmore") == "testnmore"

        # Tab escape sequence
        assert sanitize_string("test\\tmore") == "testtmore"

        # Carriage return escape sequence
        assert sanitize_string("test\\rmore") == "testrmore"

        # Quote escape sequence
        assert sanitize_string("test\\"more") == "testmore"

    def test_multiple_backslashes_with_text(self):
        """Test text with multiple backslashes throughout."""
        assert sanitize_string("\\test\\ing\\more\\") == "testingmore"

    def test_only_backslashes(self):
        """Test strings containing only backslashes."""
        assert sanitize_string("\\") == ""
        assert sanitize_string("\\\\\\\\") == ""

    def test_backslash_with_other_dangerous_chars(self):
        """Test backslash alongside other shell metacharacters."""
        # Backslash with semicolon
        assert sanitize_string("test\\;more") == "testmore"

        # Backslash with pipe
        assert sanitize_string("test\\|more") == "testmore"

        # Backslash with dollar sign
        assert sanitize_string("test\\$more") == "testmore"

    def test_empty_string_with_backslash(self):
        """Test empty string behavior with backslash."""
        assert sanitize_string("") == ""
        assert sanitize_string("\\") == ""

    def test_unicode_with_backslash(self):
        """Test that backslash is removed even with Unicode characters."""
        # Backslash with accented characters
        assert sanitize_string("café\\test") == "caftest"

        # Multiple backslashes with Unicode
        assert sanitize_string("\\naïve\\day\\") == "naveday"
