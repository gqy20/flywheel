"""Tests for Issue #1199 - Shell metacharacters in url/filename contexts."""

import pytest

from flywheel.cli import sanitize_for_security_context


class TestShellMetacharsInUrlAndFilename:
    """Test that shell metacharacters are removed in url and filename contexts.

    Issue #1199: The 'url' and 'filename' contexts should explicitly remove shell
    metacharacters to prevent command injection if these strings are mistakenly
    used in shell commands.
    """

    @pytest.mark.parametrize("context", ["url", "filename"])
    @pytest.mark.parametrize("test_input,expected_output", [
        # Test semicolon injection
        ("http://example.com;rm -rf /", "http://example.comrm -rf "),
        ("file;echo hacked", "fileecho hacked"),

        # Test pipe injection
        ("url|cat /etc/passwd", "urlcat etcpasswd"),
        ("file|malicious", "filemalicious"),

        # Test ampersand injection
        ("url&evil_command", "urlevil_command"),
        ("file&&background", "filebackground"),

        # Test backtick injection
        ("url`whoami`", "urlwhoami"),
        ("file`id`", "fileid"),

        # Test dollar sign injection
        ("url$HOME", "urlHOME"),
        ("file$(pwd)", "filepwd"),

        # Test parentheses injection
        ("url(command)", "urlcommand"),
        ("file((nested))", "filenested"),

        # Test angle brackets
        ("url<redirect>", "urlredirect"),
        ("file>output", "fileoutput"),

        # Test multiple metachars
        ("http://example.com;|&`$()", "http://examplecom"),

        # Test that safe characters are preserved
        ("normal-url_123.txt", "normal-url_123.txt"),
        ("path/to/file.txt", "path/to/file.txt"),

        # Test curly braces and backslash and percent
        ("url{test}", "urltest"),
        ("file\\path", "filepath"),
        ("url%20space", "url20space"),
    ])
    def test_shell_metachars_removed(self, context, test_input, expected_output):
        """Shell metacharacters should be removed in url and filename contexts."""
        result = sanitize_for_security_context(test_input, context=context)
        assert result == expected_output, (
            f"For context '{context}', expected '{expected_output}' but got '{result}'"
        )

    @pytest.mark.parametrize("context", ["url", "filename"])
    def test_no_shell_metachars_remain(self, context):
        """After sanitization, no shell metacharacters should remain."""
        # Define the dangerous shell metacharacters from SHELL_METACHARS_PATTERN
        dangerous_chars = {';', '|', '&', '`', '$', '(', ')', '<', '>', '{', '}', '\\', '%'}

        test_input = "test;|&`$()<>{}\\%"
        result = sanitize_for_security_context(test_input, context=context)

        # None of the dangerous characters should be in the result
        for char in dangerous_chars:
            assert char not in result, (
                f"Dangerous character '{char}' found in result: '{result}'"
            )
