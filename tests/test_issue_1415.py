"""Test for issue #1415 - Verify shlex.quote() is used in shell context.

Issue #1415: Docstring mentions using shlex.quote() for shell context,
but needs verification that it's actually implemented in the code.

This test verifies that the shell context properly uses shlex.quote()
to prevent shell injection vulnerabilities.
"""

import shlex
import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1415:
    """Test that shell context uses shlex.quote() for security.

    The docstring for sanitize_for_security_context() states that it uses
    shlex.quote() for shell context. This test verifies that this is
    actually implemented in the code.
    """

    def test_shell_context_uses_shlex_quote(self):
        """Verify shell context returns same result as shlex.quote().

        This ensures the function actually uses shlex.quote() internally
        for the shell context, as documented in the docstring.
        """
        test_cases = [
            # Simple strings
            "normal.txt",
            "file with spaces",
            # Dangerous characters that need escaping
            "file;name",
            "file|pipe",
            "file&amp",
            "file`backtick",
            "file$dollar",
            "file(paren)",
            "file{brace}",
            # Mixed dangerous content
            "file;with|many&dangerous`chars$here",
        ]

        for input_str in test_cases:
            result = sanitize_for_security_context(input_str, context="shell")
            expected = shlex.quote(input_str)

            assert result == expected, (
                f"Shell context should use shlex.quote() internally. "
                f"For input '{input_str}', expected '{expected}' but got '{result}'."
            )

    def test_shell_context_produces_quoted_output(self):
        """Verify shell context produces properly quoted output.

        The output should be wrapped in quotes (single or double) so it
        can be safely used in shell commands.
        """
        test_inputs = [
            "normal_file.txt",
            "file with spaces.txt",
            "file;semicolon.txt",
            "file'quote.txt",
        ]

        for input_str in test_inputs:
            result = sanitize_for_security_context(input_str, context="shell")

            # Result should be quoted (starts and ends with quote)
            is_quoted = (
                (result.startswith("'") and result.endswith("'")) or
                (result.startswith('"') and result.endswith('"'))
            )

            assert is_quoted, (
                f"Shell context should produce quoted output. "
                f"Input: '{input_str}', Output: '{result}'"
            )

    def test_shell_context_prevents_injection(self):
        """Test that shell context prevents injection attacks.

        Verifies that dangerous shell metacharacters are properly escaped.
        """
        dangerous_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`echo pwned`",
            "; echo injected",
        ]

        for dangerous_input in dangerous_inputs:
            sanitized = sanitize_for_security_context(dangerous_input, context="shell")

            # The sanitized version should be properly quoted
            # If we were to use this in a shell command, it would be treated
            # as a literal string, not executed
            expected = shlex.quote(dangerous_input)
            assert sanitized == expected, (
                f"Dangerous input should be properly quoted. "
                f"Input: '{dangerous_input}', Expected: '{expected}', Got: '{sanitized}'"
            )

    def test_general_context_different_from_shell(self):
        """Verify general context behaves differently from shell context.

        General context should preserve user text, while shell context
        should quote it for safety.
        """
        input_text = "file with spaces;and|semicolons"

        shell_result = sanitize_for_security_context(input_text, context="shell")
        general_result = sanitize_for_security_context(input_text, context="general")

        # Shell context should quote the result
        assert shell_result.startswith("'") or shell_result.startswith('"'), (
            f"Shell result should be quoted: {shell_result}"
        )

        # General context should NOT add quotes (preserve user intent)
        assert not general_result.startswith("'") and not general_result.startswith('"'), (
            f"General result should not add quotes: {general_result}"
        )

        # They should be different
        assert shell_result != general_result, (
            "Shell and general contexts should produce different results"
        )

    def test_empty_string_shell_context(self):
        """Test edge case: empty string in shell context."""
        result = sanitize_for_security_context("", context="shell")
        expected = shlex.quote("")

        assert result == expected, (
            f"Empty string should be properly quoted. "
            f"Expected: '{expected}', Got: '{result}'"
        )

    def test_newline_and_control_chars_removed_before_quoting(self):
        """Test that control chars are removed before shlex.quote().

        The implementation should remove control characters first,
        then apply shlex.quote() to the cleaned string.
        """
        input_with_control = "file\nname\t\r\n;dangerous"

        result = sanitize_for_security_context(input_with_control, context="shell")

        # Control characters should be removed
        assert "\n" not in result
        assert "\t" not in result
        assert "\r" not in result

        # The result should still be quoted
        assert result.startswith("'") or result.startswith('"')

        # Verify it matches shlex.quote() of the cleaned input
        # (after removing control chars)
        import re
        CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1F\x7F]')
        cleaned = CONTROL_CHARS_PATTERN.sub('', input_with_control)
        expected = shlex.quote(cleaned)

        assert result == expected, (
            f"Control chars should be removed before quoting. "
            f"Expected: '{expected}', Got: '{result}'"
        )
