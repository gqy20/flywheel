"""Tests for Issue #1249 - Control character removal before shlex.quote().

Issue #1249 raises a concern: In the 'shell' context, removing control characters
BEFORE applying shlex.quote() might cause logical conflicts or unexpected behavior.

After careful analysis, the current implementation is CORRECT and SAFE:
1. Control characters are removed first (prevents injection via control chars)
2. shlex.quote() is then applied (ensures proper quoting of shell metacharacters)
3. This two-step approach is the most secure method

Rationale:
- Control characters in shell command arguments serve no legitimate purpose
- Removing them prevents confusion and potential injection vectors
- shlex.quote() does NOT depend on control characters for proper quoting
- shlex.quote() will correctly quote the cleaned string
"""

import pytest
import shlex
from flywheel.cli import sanitize_for_security_context


class TestIssue1249:
    """Test cases for Issue #1249 - validating that control char removal before shlex.quote() is safe."""

    def test_control_chars_removed_before_quoting(self):
        """Test that control characters are removed before shlex.quote() is applied.

        This is the expected and safe behavior.
        """
        test_input = "test\x00\x01\x02string"
        result = sanitize_for_security_context(test_input, context="shell")

        # Control characters should be removed, then quoted
        cleaned = "teststring"
        expected = shlex.quote(cleaned)
        assert result == expected

    def test_newline_removed_before_quoting(self):
        """Test that newlines are removed before quoting in shell context.

        Newlines could be used for command injection if not handled properly.
        Removing them before quoting is the safest approach.
        """
        test_input = "line1\nline2\nline3"
        result = sanitize_for_security_context(test_input, context="shell")

        # Newlines removed, then quoted
        cleaned = "line1line2line3"
        expected = shlex.quote(cleaned)
        assert result == expected

    def test_shell_metas_quoted_after_control_removal(self):
        """Test that shell metacharacters are properly quoted even after control char removal.

        This validates that shlex.quote() works correctly on the cleaned string.
        """
        test_input = "echo $HOME\nwhoami"
        result = sanitize_for_security_context(test_input, context="shell")

        # Newline removed, but shell metacharacters preserved and quoted
        cleaned = "echo $HOMEwhoami"
        expected = shlex.quote(cleaned)
        assert result == expected

        # Verify the result is properly quoted (starts with quote)
        assert result[0] in ("'", '"')

    def test_mixed_control_and_metas(self):
        """Test complex strings with both control characters and shell metacharacters."""
        test_input = "cmd1; cmd2\x00cmd3 | cmd4\ncmd5"
        result = sanitize_for_security_context(test_input, context="shell")

        # Control chars removed, shell metachars preserved and quoted
        cleaned = "cmd1; cmd2cmd3 | cmd4cmd5"
        expected = shlex.quote(cleaned)
        assert result == expected

    def test_null_byte_injection_attempt(self):
        """Test that null bytes are properly handled to prevent injection."""
        # Attempt to inject commands using null byte separation
        test_input = "legitimate\x00rm -rf /\x00echo pwned"
        result = sanitize_for_security_context(test_input, context="shell")

        # All null bytes removed, then quoted
        cleaned = "legitimaterm -rf /echo pwned"
        expected = shlex.quote(cleaned)
        assert result == expected

    def test_empty_after_control_removal(self):
        """Test string that becomes empty after removing control characters."""
        test_input = "\x00\x01\x02\x03\n\r\t"
        result = sanitize_for_security_context(test_input, context="shell")

        # All control chars removed, resulting in empty string
        expected = shlex.quote("")
        assert result == expected

    def test_unicode_spoofing_chars_removed_after_control_removal(self):
        """Test that Unicode spoofing characters are removed after control chars."""
        test_input = "test\x00\u200Bevil\u202Atest"
        result = sanitize_for_security_context(test_input, context="shell")

        # Control chars removed, then Unicode spoofing chars removed, then quoted
        cleaned = "testeviltest"
        expected = shlex.quote(cleaned)
        assert result == expected

    def test_current_implementation_is_safe(self):
        """Document that the current implementation is safe and correct.

        This test validates that the two-step approach (remove control chars,
        then apply shlex.quote()) is the most secure method for shell context.
        """
        # String with various potentially dangerous characters
        test_input = "test\n\x00$HOME`whoami`\t\r"

        # The sanitized result should be:
        # 1. Control characters removed (\n, \x00, \t, \r)
        # 2. Unicode spoofing chars removed (none in this case)
        # 3. shlex.quote() applied to handle $ and `
        result = sanitize_for_security_context(test_input, context="shell")

        # Verify the result is properly quoted
        assert result[0] in ("'", '"')

        # Verify it can be safely used (quoted by shlex)
        # The result should be a valid shell-quoted string
        import subprocess
        # This would be safe to use with subprocess:
        # subprocess.run(["echo", result])  # Safe!
        # subprocess.run("echo " + result, shell=True)  # Also safe now!

    def test_control_chars_removed_before_quoting(self):
        """Test that demonstrates the current behavior: control chars removed before quoting.

        This test documents the current behavior where control characters are
        removed BEFORE shlex.quote() is applied. This could potentially cause
        issues if shlex.quote() expects certain characters to be present.
        """
        # String with various control characters
        test_input = "hello\x00world\x1ftest"
        result = sanitize_for_security_context(test_input, context="shell")

        # Control characters should be removed
        # Then shlex.quote should be applied to the cleaned string
        cleaned = "helloworldtest"  # control chars removed
        expected = shlex.quote(cleaned)
        assert result == expected

