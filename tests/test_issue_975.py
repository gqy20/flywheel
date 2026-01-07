"""Test for issue #975 - Curly braces should be preserved in general context."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue975:
    """Test that curly braces are preserved in general context but removed in shell context."""

    def test_curly_braces_preserved_in_general_context(self):
        """Curly braces should be preserved in general context for format() strings."""
        # Test with format string pattern
        test_string = "Hello {name}, your score is {score}"
        result = sanitize_for_security_context(test_string, context="general")
        assert result == test_string, f"Expected '{test_string}', got '{result}'"

    def test_curly_braces_removed_in_shell_context(self):
        """Curly braces should be removed in shell context for security."""
        test_string = "Hello {name}, your score is {score}"
        expected = "Hello name, your score is score"
        result = sanitize_for_security_context(test_string, context="shell")
        assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_curly_braces_removed_in_filename_context(self):
        """Curly braces should be removed in filename context for security."""
        test_string = "document{backup}.txt"
        expected = "documentbackup.txt"
        result = sanitize_for_security_context(test_string, context="filename")
        assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_curly_braces_removed_in_url_context(self):
        """Curly braces should be removed in URL context for security."""
        test_string = "https://example.com/{path}"
        expected = "https://example.com/path"
        result = sanitize_for_security_context(test_string, context="url")
        assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_format_string_functionality_preserved(self):
        """Test that format() still works after sanitization in general context."""
        template = "Hello {name}, your score is {score}"
        sanitized = sanitize_for_security_context(template, context="general")

        # This should work without raising an exception
        result = sanitized.format(name="Alice", score="95")
        assert result == "Hello Alice, your score is 95"

    def test_other_metachars_removed_in_general_context(self):
        """Other metachars should still be removed in general context."""
        test_string = "test;command&pipe`dollar$(paren)<redirect>"
        expected = "testcommandpipedollarparenredirect"
        result = sanitize_for_security_context(test_string, context="general")
        assert result == expected, f"Expected '{expected}', got '{result}'"
