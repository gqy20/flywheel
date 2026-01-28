"""Test for issue #1280 - Reduce default max_length in sanitize_for_security_context.

This test verifies that the default max_length parameter in sanitize_for_security_context
is set to a reasonable value (4096) instead of the previous 100,000, which could cause
memory issues or processing delays for CLI tools handling user input.

Issue: #1280
Security: Reduce default max_length to prevent potential DoS attacks
"""

import pytest
from flywheel.cli import sanitize_for_security_context, remove_control_chars


class TestIssue1280:
    """Test cases for issue #1280 - default max_length parameter."""

    def test_sanitize_for_security_context_default_max_length(self):
        """Test that sanitize_for_security_context has reasonable default max_length."""
        # Create a string longer than 4096 but shorter than 100,000
        long_string = "a" * 5000

        # With the fix, this should be truncated to 4096 characters
        result = sanitize_for_security_context(long_string)

        # The result should be truncated to the new default (4096)
        assert len(result) == 4096, (
            f"Expected default max_length to be 4096, but got {len(result)} characters. "
            f"This indicates the default max_length is still set to 100,000."
        )

    def test_remove_control_chars_default_max_length(self):
        """Test that remove_control_chars has reasonable default max_length."""
        # Create a string longer than 4096 but shorter than 100,000
        long_string = "b" * 5000

        # With the fix, this should be truncated to 4096 characters
        result = remove_control_chars(long_string)

        # The result should be truncated to the new default (4096)
        assert len(result) == 4096, (
            f"Expected default max_length to be 4096, but got {len(result)} characters. "
            f"This indicates the default max_length is still set to 100,000."
        )

    def test_sanitize_for_security_context_explicit_max_length_still_works(self):
        """Test that explicit max_length parameter still works correctly."""
        # Create a long string
        long_string = "c" * 10000

        # Explicitly pass a larger max_length
        result = sanitize_for_security_context(long_string, max_length=10000)

        # Should respect the explicit parameter
        assert len(result) == 10000

    def test_sanitize_for_security_context_short_string_unchanged(self):
        """Test that short strings are not affected by the max_length change."""
        short_string = "Hello, World!"

        result = sanitize_for_security_context(short_string)

        # Short strings should remain unchanged
        assert result == short_string
