"""Test for issue #974 - Percent sign should be preserved in general context."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue974:
    """Test that percent sign is preserved in general context but removed in security contexts."""

    def test_percent_sign_preserved_in_general_context(self):
        """Percent sign should be preserved in general context for Formatter functionality."""
        # Test case with percent sign in general context
        input_string = "Progress: 50% complete"
        result = sanitize_for_security_context(input_string, context="general")

        # Percent sign should be preserved in general context
        assert "%" in result, f"Percent sign was removed in general context: {result}"
        assert "50%" in result, f"Expected '50%' but got: {result}"

    def test_percent_sign_removed_in_shell_context(self):
        """Percent sign should be removed in shell context for security."""
        # Test case with percent sign in shell context
        input_string = "Progress: 50% complete"
        result = sanitize_for_security_context(input_string, context="shell")

        # Percent sign should be removed in shell context
        assert "%" not in result, f"Percent sign should be removed in shell context: {result}"
        assert "50 complete" in result, f"Expected '50 complete' but got: {result}"

    def test_percent_sign_removed_in_url_context(self):
        """Percent sign should be removed in url context for security."""
        # Test case with percent sign in url context
        input_string = "file%20name.txt"
        result = sanitize_for_security_context(input_string, context="url")

        # Percent sign should be removed in url context
        assert "%" not in result, f"Percent sign should be removed in url context: {result}"

    def test_percent_sign_removed_in_filename_context(self):
        """Percent sign should be removed in filename context for security."""
        # Test case with percent sign in filename context
        input_string = "file%20name.txt"
        result = sanitize_for_security_context(input_string, context="filename")

        # Percent sign should be removed in filename context
        assert "%" not in result, f"Percent sign should be removed in filename context: {result}"

    def test_format_string_with_percent(self):
        """Test that format strings with percent signs work in general context."""
        # This is important for Formatter functionality
        input_string = "Status: %s, Progress: %d%%"
        result = sanitize_for_security_context(input_string, context="general")

        # Percent signs should be preserved
        assert "%%" in result or "%" in result, f"Percent signs should be preserved: {result}"
