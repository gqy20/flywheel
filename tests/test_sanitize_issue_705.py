"""Test cases for Issue #705 - Backslash removal causes data corruption.

Issue #705 reports that sanitize_string removes backslashes, which can cause
data corruption for:
- Windows paths (C:\Users\...)
- Escape sequences
- Markdown syntax

The issue suggests that if storage backends support parameterized queries,
backslashes don't need to be removed. Removing them breaks legitimate content.

These tests verify that backslashes are preserved to prevent data corruption.
"""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringIssue705:
    """Tests for verify that sanitize_string preserves backslashes.

    Backslashes are legitimate characters in many contexts:
    - Windows file paths (C:\Users\Name\Documents\file.txt)
    - Escape sequences in text
    - Markdown syntax with backslashes
    - Regular expressions
    - LaTeX and other markup languages

    Issue #705: Removing backslashes causes data corruption and should be avoided
    when storage backends support parameterized queries.
    """

    def test_preserves_windows_path_backslashes(self):
        """Test that Windows paths with backslashes are preserved."""
        # Windows paths use backslashes as directory separators
        input_str = r"C:\Users\Name\Documents\file.txt"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in Windows paths should be preserved"
        assert result == r"C:\Users\Name\Documents\file.txt", \
            "Windows paths should remain intact"

    def test_preserves_unc_paths(self):
        """Test that UNC paths with backslashes are preserved."""
        # UNC (Universal Naming Convention) paths
        input_str = r"\\server\share\folder\file.txt"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in UNC paths should be preserved"
        assert result == r"\\server\share\folder\file.txt", \
            "UNC paths should remain intact"

    def test_preserves_relative_windows_paths(self):
        """Test that relative Windows paths are preserved."""
        # Relative paths with backslashes
        input_str = r"..\..\Documents\file.txt"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in relative paths should be preserved"

    def test_preserves_markdown_backslash_escapes(self):
        """Test that Markdown backslash escapes are preserved."""
        # Markdown uses backslash to escape special characters
        input_str = r"This is \*italic\* and \`\`code\`\` in Markdown"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in Markdown escapes should be preserved"

    def test_preserves_regex_backslashes(self):
        """Test that regex patterns with backslashes are preserved."""
        # Regex patterns use backslashes for escaping
        input_str = r"Pattern: \d+\.\w+"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in regex patterns should be preserved"

    def test_preserves_latex_backslashes(self):
        """Test that LaTeX commands with backslashes are preserved."""
        # LaTeX commands start with backslash
        input_str = r"Use \textbf{bold} and \emph{italic}"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in LaTeX commands should be preserved"

    def test_preserves_escape_sequences_in_text(self):
        """Test that escape sequences in text content are preserved."""
        # Escape sequences in documentation or code snippets
        input_str = r"Use \n for newline and \t for tab"
        result = sanitize_string(input_str)
        assert '\\' in result, "Backslashes in escape sequences should be preserved"

    def test_still_removes_dangerous_shell_operators(self):
        """Test that dangerous shell operators are still removed."""
        # Shell injection metacharacters should still be removed
        input_str = "Test; echo hacked | cat"
        result = sanitize_string(input_str)
        assert ';' not in result, "Shell operators should be removed"
        assert '|' not in result, "Pipe operators should be removed"
        assert 'echo' in result, "Legitimate text should be preserved"

    def test_still_removes_curly_braces_for_format_string_protection(self):
        """Test that curly braces are still removed to prevent format string attacks."""
        # Curly braces should still be removed as per Issue #690
        input_str = "Test {variable} String"
        result = sanitize_string(input_str)
        assert '{' not in result, "Opening curly brace should be removed"
        assert '}' not in result, "Closing curly brace should be removed"

    def test_backslash_without_context_is_preserved(self):
        """Test that a single backslash is preserved."""
        input_str = "Test\\String"
        result = sanitize_string(input_str)
        assert '\\' in result, "Single backslash should be preserved"
