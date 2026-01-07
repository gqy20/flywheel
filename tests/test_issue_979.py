"""Tests for Issue #979 - Shell metacharacter filtering in general context.

Issue #979 points out that in a general context (non-security-sensitive),
the remove_control_chars function should preserve shell metacharacters since
they are legitimate characters in user text. The function is for data normalization,
not security protection.

The problem is at line 145 (now line 291 in current code) where shell metacharacters
are removed even in general context. These characters should only be removed in
security-sensitive contexts (shell, url, filename) which are handled by
sanitize_for_security_context().
"""

import pytest

from flywheel.cli import remove_control_chars, sanitize_for_security_context


class TestIssue979ShellMetacharInGeneralContext:
    """Tests for Issue #979 - Shell metacharacters in general context."""

    def test_general_context_preserves_pipe(self):
        """General context should preserve pipe character."""
        # Pipe is a legitimate character in general text
        input_text = "Use | for separating options"
        result = remove_control_chars(input_text)
        assert "|" in result, "Pipe character should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_semicolon(self):
        """General context should preserve semicolon."""
        # Semicolon is legitimate in general text
        input_text = "Note: this is important; remember it"
        result = remove_control_chars(input_text)
        assert ";" in result, "Semicolon should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_ampersand(self):
        """General context should preserve ampersand."""
        # Ampersand is legitimate in general text
        input_text = "Johnson & Johnson"
        result = remove_control_chars(input_text)
        assert "&" in result, "Ampersand should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_dollar(self):
        """General context should preserve dollar sign."""
        # Dollar sign is legitimate in general text
        input_text = "Cost: $100"
        result = remove_control_chars(input_text)
        assert "$" in result, "Dollar sign should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_parentheses(self):
        """General context should preserve parentheses."""
        # Parentheses are legitimate in general text
        input_text = "See chapter (5) for details"
        result = remove_control_chars(input_text)
        assert "(" in result and ")" in result, "Parentheses should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_angle_brackets(self):
        """General context should preserve angle brackets."""
        # Angle brackets are legitimate in general text (e.g., <placeholder>)
        input_text = "Enter your <name> here"
        result = remove_control_chars(input_text)
        assert "<" in result and ">" in result, "Angle brackets should be preserved in general context"
        assert result == input_text

    def test_general_context_preserves_backtick(self):
        """General context should preserve backtick."""
        # Backtick is legitimate in general text (e.g., code snippets)
        input_text = "Use `print('hello')` for output"
        result = remove_control_chars(input_text)
        assert "`" in result, "Backtick should be preserved in general context"
        assert result == input_text

    def test_security_context_removes_shell_metachars(self):
        """Security context (shell) should remove shell metacharacters."""
        # In security contexts, shell metachars should be removed
        input_text = "test;command|pipe&exec"
        result = sanitize_for_security_context(input_text, context="shell")
        assert ";" not in result, "Semicolon should be removed in shell context"
        assert "|" not in result, "Pipe should be removed in shell context"
        assert "&" not in result, "Ampersand should be removed in shell context"

    def test_url_context_removes_shell_metachars(self):
        """Security context (url) should remove shell metacharacters."""
        input_text = "url;with|chars&that$are(dangerous)"
        result = sanitize_for_security_context(input_text, context="url")
        assert ";" not in result, "Semicolon should be removed in URL context"
        assert "|" not in result, "Pipe should be removed in URL context"

    def test_filename_context_removes_shell_metachars(self):
        """Security context (filename) should remove shell metacharacters."""
        input_text = "file;name|with&bad$chars()"
        result = sanitize_for_security_context(input_text, context="filename")
        assert ";" not in result, "Semicolon should be removed in filename context"
        assert "|" not in result, "Pipe should be removed in filename context"

    def test_real_world_todo_title_example(self):
        """Real-world example: Todo title with legitimate shell-like characters."""
        # These are all legitimate uses in todo titles
        test_cases = [
            "Review PR #123 (bug fix)",
            "Meeting: Q1 planning; Q2 review",
            "Cost analysis: $500 vs $1000",
            "Documentation: See chapter 5 (sections 5.1-5.5)",
            "Code review: check `if (x > 0) { return x; }`",
            "Format: use `<key>: <value>` pattern",
        ]

        for test_case in test_cases:
            result = remove_control_chars(test_case)
            # All these legitimate uses should be preserved
            # The function should only remove control characters, not shell metachars
            # Note: Currently this test will FAIL because remove_control_chars incorrectly
            # removes shell metacharacters. This is the bug that Issue #979 reports.
            assert result == test_case, f"Text should be preserved: {test_case}"

    def test_warning_in_docstring(self):
        """Verify function documentation warns about not providing security protection."""
        # The function documentation should clearly state it does NOT provide
        # shell injection protection
        docstring = remove_control_chars.__doc__
        assert "does NOT provide security protection" in docstring or \
               "does NOT prevent" in docstring, \
               "Function should warn that it doesn't provide security protection"
        assert "shell" in docstring.lower(), \
               "Documentation should mention shell commands"
