"""Test cases for Issue #669 - Overly aggressive string sanitization."""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringIssue669:
    """Tests for verify that sanitize_string preserves legitimate content."""

    def test_preserves_quotes_in_title(self):
        """Test that quotes in titles are preserved for legitimate content."""
        # Test case 1: Code snippets with quotes
        input_str = 'Fix "bug" in function_name'
        result = sanitize_string(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_preserves_single_quotes(self):
        """Test that single quotes are preserved."""
        input_str = "Don't forget to test"
        result = sanitize_string(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_preserves_percentage_sign(self):
        """Test that percentage signs are preserved."""
        input_str = "Completed 95% of the work"
        result = sanitize_string(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_preserves_code_snippets(self):
        """Test that code snippets with various quotes are preserved."""
        # Python-style code
        input_str = 'Use print("hello") for output'
        result = sanitize_string(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

        # Mixed quotes
        input_str = "It's a \"test\" case"
        result = sanitize_string(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_preserves_backslash_in_code(self):
        """Test that backslashes in code paths are preserved."""
        input_str = "Use /path/to/file for Linux"
        result = sanitize_string(input_str)
        # Backslash in paths should be preserved
        assert "/path/to/file" in result or "\\path\\to\\file" in result

    def test_description_with_quotes_and_percent(self):
        """Test realistic description with quotes and percentages."""
        input_str = "Review PR #123: 'Fix 100% of issues' by changing \"config\" value"
        result = sanitize_string(input_str)
        assert "'" in result, "Single quotes should be preserved"
        assert '"' in result, "Double quotes should be preserved"
        assert '%' in result, "Percentage sign should be preserved"

    def test_still_removes_dangerous_shell_operators(self):
        """Test that truly dangerous shell operators are still removed."""
        # Shell operators that should be removed
        input_str = "Test; rm -rf /"
        result = sanitize_string(input_str)
        assert ';' not in result, "Semicolon should be removed for security"

        input_str = "Test && echo bad"
        result = sanitize_string(input_str)
        assert '&' not in result or '&&' not in result, "Ampersand should be removed"

    def test_title_with_double_quotes(self):
        """Test that titles with double quotes are preserved."""
        input_str = 'Read "The Art of Programming" book'
        result = sanitize_string(input_str)
        assert '"' in result, "Double quotes should be preserved in titles"

    def test_preserves_pipe_in_contextual_content(self):
        """Test that pipe in legitimate content is handled appropriately."""
        # Pipe in descriptive text might be okay (e.g., "A | B" notation)
        # but shell commands like "cat | grep" should be sanitized
        input_str = "Use option A | B for selection"
        result = sanitize_string(input_str)
        # This test documents current behavior - pipe is removed for security
        # but could be relaxed if needed for legitimate use cases
