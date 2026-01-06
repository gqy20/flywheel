"""Test for Issue #824 - sanitize_string should not be used for shell safety

This test verifies that sanitize_string function correctly documents its purpose
and limitations. The function is designed for data storage cleaning, NOT for
shell injection prevention. For shell command execution, subprocess with list
arguments (shell=False) or shlex.quote() should be used instead.
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue824ShellInjectionDocumentation:
    """Test suite for Issue #824 - Clarify sanitize_string is not for shell safety."""

    def test_single_quote_preserved_for_legitimate_content(self):
        """Test that single quotes are preserved for legitimate text content.

        The function preserves quotes because they are needed for legitimate
        text content (e.g., code snippets, contractions, quoted text).
        """
        legitimate_input = "Don't forget to 'review' the code"
        result = sanitize_string(legitimate_input)
        # Quotes should be preserved for legitimate content
        assert "'" in result, "Single quotes preserved for legitimate content"

    def test_double_quote_preserved_for_legitimate_content(self):
        """Test that double quotes are preserved for legitimate text content."""
        legitimate_input = 'She said "hello" and waved'
        result = sanitize_string(legitimate_input)
        # Quotes should be preserved for legitimate content
        assert '"' in result, "Double quotes preserved for legitimate content"

    def test_percent_sign_preserved_for_legitimate_content(self):
        """Test that percent signs are preserved for legitimate text content."""
        legitimate_input = "Complete 50% of the work, format: %s %d"
        result = sanitize_string(legitimate_input)
        # Percent signs should be preserved for legitimate content
        assert '%' in result, "Percent signs preserved for legitimate content"

    def test_shell_metacharacters_removed_for_data_format_safety(self):
        """Test that certain metacharacters are removed to prevent data format issues.

        The function removes some metacharacters that could interfere with data
        formats or display systems, but this does NOT provide shell injection protection.
        """
        input_with_metachars = "cmd1; cmd2 | cmd3 & cmd4 `whoami` $(date)"
        result = sanitize_string(input_with_metachars)
        # These characters are removed for data format safety
        assert ';' not in result, "Semicolons removed"
        assert '|' not in result, "Pipes removed"
        assert '&' not in result, "Ampersands removed"
        assert '`' not in result, "Backticks removed"
        assert '$' not in result, "Dollar signs removed"

    def test_function_documentation_clarifies_not_shell_safe(self):
        """Test that the function's docstring clarifies it's not for shell safety.

        The fix for Issue #824 adds clear documentation that this function is
        NOT suitable for preventing shell injection.
        """
        docstring = sanitize_string.__doc__
        # The documentation should clearly state this is NOT for shell safety
        assert 'NOT suitable for preventing shell injection' in docstring or \
               'NOT suitable for shell command safety' in docstring, \
               "Function docstring should clarify it's not for shell safety"
        assert 'subprocess' in docstring, \
               "Function should recommend subprocess for shell commands"
        assert 'shlex.quote' in docstring, \
               "Function should recommend shlex.quote for shell commands"

    def test_dangerous_characters_in_shell_context(self):
        """Test that demonstrates the function is not safe for shell contexts.

        This test documents that the function preserves quotes which would be
        dangerous in shell contexts, reinforcing that the function should NOT
        be used for shell command safety.
        """
        # Input that would be dangerous in shell context
        malicious_input = """'; echo "hacked"; #'"""
        result = sanitize_string(malicious_input)
        # The function preserves quotes (for legitimate text content)
        # This demonstrates it's NOT safe for shell use
        assert "'" in result or '"' in result, \
               "Quotes are preserved - function is NOT shell-safe"

    def test_curly_braces_removed_for_format_string_safety(self):
        """Test that curly braces are removed to prevent format string attacks.

        While the function is not for shell safety, it does remove curly braces
        to prevent format string attacks when sanitized data is used in f-strings
        or .format() calls.
        """
        input_with_braces = "Use {variable} for formatting"
        result = sanitize_string(input_with_braces)
        assert '{' not in result, "Opening curly brace removed"
        assert '}' not in result, "Closing curly brace removed"

    def test_backslashes_removed_to_prevent_escape_sequences(self):
        """Test that backslashes are removed to prevent escape sequence issues.

        Backslashes are removed because they can cause escape sequence issues
        in various contexts (not just shell).
        """
        input_with_backslash = "path\\to\\file\\with\\backslashes"
        result = sanitize_string(input_with_backslash)
        assert '\\' not in result, "Backslashes removed"

    def test_control_characters_replaced_with_spaces(self):
        """Test that control characters are replaced with spaces.

        Control characters are replaced with spaces to preserve word separation
        and data integrity (Issue #815).
        """
        input_with_newlines = "Hello\nWorld\r\nTest"
        result = sanitize_string(input_with_newlines)
        # Control chars should be replaced with spaces, not removed
        assert 'Hello World' in result, "Newlines replaced with spaces"
