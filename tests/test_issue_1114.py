"""Test for issue #1114 - False sense of security in 'shell' context.

Issue #1114: The current implementation of sanitize_for_security_context with
context="shell" removes shell metacharacters like ;, |, &, `, $, (, ), <, >, {, }, \, %
but this creates a FALSE sense of security. Removing metacharacters does NOT make
a string safe for shell injection if it is later concatenated into a shell command.

The FIX: Instead of removing characters, the function should use shlex.quote() to
properly escape the entire string for safe use in shell commands. This is the
ONLY correct way to make a string safe for shell usage.
"""

import subprocess
import shlex
import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1114:
    """Test that shell context uses proper escaping, not character removal.

    The old implementation removed shell metacharacters, which is insecure because:
    1. It doesn't protect against all injection vectors (e.g., newlines, variable expansion)
    2. It gives a false sense of security
    3. It mutates user data in ways that may not be intended

    The new implementation should use shlex.quote() which properly escapes
    the entire string for safe shell usage.
    """

    def test_shell_context_returns_quoted_string(self):
        """Test that shell context returns a properly quoted string.

        The returned string should be wrapped in quotes and have internal
        special characters properly escaped so it can be safely used in
        shell commands via os.system() or similar.
        """
        # Test with various dangerous inputs
        dangerous_inputs = [
            "normal.txt",
            "file with spaces.txt",
            "file;with;semicolons.txt",
            "file|with|pipes.txt",
            "file&with&ampersands.txt",
            "file`with`backticks.txt",
            "file$with$dollars.txt",
            "file(with)parentheses.txt",
            "file<with>brackets.txt",
            "file{with}braces.txt",
            "file\\with\\backslash.txt",
            "file%with%percent.txt",
            "file'with'single'quotes.txt",
            'file"with"double"quotes.txt',
            "file\nwith\nnewlines.txt",
            "file\twith\ttabs.txt",
        ]

        for input_str in dangerous_inputs:
            result = sanitize_for_security_context(input_str, context="shell")

            # The result should be a quoted version of the input
            # shlex.quote() adds quotes and escapes special characters
            expected = shlex.quote(input_str)

            assert result == expected, (
                f"For shell context, expected shlex.quote() result '{expected}' "
                f"but got '{result}' for input '{input_str}'. "
                f"The shell context must use proper escaping, not character removal."
            )

    def test_shell_context_produces_safe_shell_string(self):
        """Test that the result is actually safe for shell usage.

        This test verifies that the quoted string can be safely used
        in a shell command without injection vulnerabilities.
        """
        test_inputs = [
            "normal_file.txt",
            "file with spaces.txt",
            "file'with'quotes.txt",
            "file;with;semicolons.txt",
            "file`whoami`.txt",
            'file"$(whoami)".txt',
        ]

        for input_str in test_inputs:
            sanitized = sanitize_for_security_context(input_str, context="shell")

            # Verify it's properly quoted by checking it starts and ends with quotes
            # (shlex.quote wraps strings in single quotes unless they contain single quotes)
            if "'" in input_str:
                # If input contains single quotes, shlex.quote uses double quotes
                # and escapes the single quotes
                assert (sanitized.startswith('"') and sanitized.endswith('"')) or \
                       (sanitized.startswith("'") and sanitized.endswith("'")), \
                       f"Sanitized string should be quoted: {sanitized}"
            else:
                # Normal case: wrapped in single quotes
                assert sanitized.startswith("'") and sanitized.endswith("'"), \
                       f"Sanitized string should be wrapped in single quotes: {sanitized}"

            # Verify the sanitized version, when used in a shell command,
            # would be interpreted as a single argument (not split on spaces, etc.)
            # We can test this by comparing the parsed result
            # Use shell=False with subprocess to avoid shell interpretation
            # and shell=True with the quoted string
            cmd_safe = f"echo {sanitized}"
            result = subprocess.run(
                cmd_safe,
                shell=True,
                capture_output=True,
                text=True
            )

            # The output should match the original input (minus the newline echo adds)
            assert result.stdout.strip() == input_str, (
                f"When used in shell command, sanitized string should produce "
                f"original input. Expected '{input_str}' but got '{result.stdout.strip()}'. "
                f"This means the escaping is not safe for shell usage."
            )

    def test_general_context_not_affected(self):
        """Test that general context behavior is unchanged.

        The fix should only affect shell context. General context should
        continue to preserve user text as-is (except for normalization).
        """
        input_text = "Cost: $100 (discount) & save; use `code` | see <docs>"

        result = sanitize_for_security_context(input_text, context="general")

        # In general context, shell metachars should be preserved
        assert ";" in result
        assert "|" in result
        assert "&" in result
        assert "`" in result
        assert "$" in result
        assert "(" in result and ")" in result
        assert "<" in result and ">" in result

    def test_url_and_filename_context_not_affected(self):
        """Test that url and filename contexts are not affected by this change.

        Those contexts should continue their current behavior.
        """
        # URL context - NFKC normalization, remove shell metachars
        url_input = "http://ｅｘａｍｐｌｅ．ｃｏｍ/path;param=value"
        url_result = sanitize_for_security_context(url_input, context="url")
        # Should use NFKC normalization (converts fullwidth chars)
        assert "example.com" in url_result

        # Filename context - NFKC normalization, remove shell metachars
        filename_input = "ｆｉｌｅｎａｍｅ．ｔｘｔ;dangerous"
        filename_result = sanitize_for_security_context(filename_input, context="filename")
        # Should use NFKC normalization
        assert "filename.txt" in filename_result

    def test_empty_string_shell_context(self):
        """Test edge case of empty string in shell context."""
        result = sanitize_for_security_context("", context="shell")
        expected = shlex.quote("")
        assert result == expected, f"Empty string should be properly quoted: expected '{expected}', got '{result}'"

    def test_string_with_only_special_chars_shell_context(self):
        """Test edge case of string with only special characters."""
        input_str = ";|$&()`{}\\%"
        result = sanitize_for_security_context(input_str, context="shell")
        expected = shlex.quote(input_str)
        assert result == expected, (
            f"String with only special chars should be properly quoted: "
            f"expected '{expected}', got '{result}'"
        )
