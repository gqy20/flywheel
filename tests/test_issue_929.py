"""Test for Issue #929 - Incomplete removal of format string specifiers.

This test verifies that remove_control_chars() removes percent signs (%)
to prevent format string injection when the normalized string is used in
legacy % formatting (e.g., logger.info(msg)).
"""

import pytest
from flywheel.cli import remove_control_chars


class TestIssue929:
    """Test cases for Issue #929 - Percent sign removal."""

    def test_remove_percent_sign_single(self):
        """Test that a single percent sign is removed."""
        input_str = "test%message"
        result = remove_control_chars(input_str)
        assert "%" not in result, "Percent sign should be removed to prevent format string injection"
        assert result == "testmessage"

    def test_remove_percent_sign_multiple(self):
        """Test that multiple percent signs are removed."""
        input_str = "test%s%message%d"
        result = remove_control_chars(input_str)
        assert "%" not in result, "All percent signs should be removed"
        assert result == "testsmessage d"

    def test_remove_percent_with_format_specifiers(self):
        """Test that percent signs with format specifiers are removed."""
        input_str = "User: %s, ID: %d, Value: %f"
        result = remove_control_chars(input_str)
        assert "%" not in result, "Percent signs with format specifiers should be removed"
        assert result == "User: s, ID: d, Value: f"

    def test_remove_percent_with_string_attack(self):
        """Test that potential format string attack vectors are removed."""
        # Simulate a format string injection attempt
        input_str = "normal %(secret)s text"
        result = remove_control_chars(input_str)
        assert "%" not in result, "Percent signs in potential attack vectors should be removed"
        assert result == "normal (secret)s text"

    def test_percent_sign_in_text(self):
        """Test that percent signs in normal text are also removed."""
        # Even legitimate use cases of % should be removed to prevent accidental format string bugs
        input_str = "Progress: 50% complete"
        result = remove_control_chars(input_str)
        assert "%" not in result, "All percent signs should be removed regardless of context"
        # Note: This may change behavior but is necessary for security
        assert result == "Progress: 50 complete"
