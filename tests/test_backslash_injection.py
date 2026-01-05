"""Test for backslash injection vulnerability (Issue #730)."""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_has_security_warning():
    """Test that sanitize_string function documents security risks.

    The function preserves backslashes for Windows paths, but if the
    sanitized string is passed to a shell command (e.g., via os.system
    or subprocess.run with shell=True), a trailing backslash can escape
    the closing quote and inject arbitrary commands.

    This test verifies that the function's docstring includes explicit
    warnings about this security concern.
    """
    docstring = sanitize_string.__doc__

    # Verify the docstring exists
    assert docstring is not None, "Function must have documentation"

    # Check for explicit warnings about backslash risks
    security_keywords = [
        "backslash",
        "shell",
        "injection",
        "parameterized",
    ]

    docstring_lower = docstring.lower()
    found_warnings = [keyword for keyword in security_keywords if keyword in docstring_lower]

    # Should have at least 2 of these security-related terms
    assert len(found_warnings) >= 2, (
        f"Docstring must warn about security risks. "
        f"Found keywords: {found_warnings}. "
        f"Should include warnings about backslash, shell injection, "
        f"and the need for parameterized queries."
    )

    # Specifically mention that output should not be used in shell commands
    assert any(
        term in docstring_lower for term in ["shell command", "os.system", "subprocess"]
    ), "Docstring must explicitly warn against using output in shell commands"

    # Mention parameterized queries as the safe alternative
    assert "parameterized" in docstring_lower, (
        "Docstring must recommend parameterized queries as safe alternative"
    )


def test_backslash_preservation_behavior():
    """Test that backslashes are preserved (documenting the risk).

    This test documents the current behavior: backslashes are preserved
    for legitimate use cases (Windows paths, Markdown, regex). However,
    this behavior is dangerous if the output is used in shell commands.
    """
    # Legitimate use cases that require backslash preservation
    test_cases = [
        # Windows paths
        ("C:\\Users\\Admin\\file.txt", "Windows path"),
        # Markdown escapes
        ("\\*not bold\\*", "Markdown escape"),
        # Regex patterns
        ("\\d+", "Regex pattern"),
        # Trailing backslash (dangerous in shell context!)
        ("path\\", "Trailing backslash"),
    ]

    for input_str, description in test_cases:
        result = sanitize_string(input_str)
        assert "\\" in result, f"{description}: backslashes should be preserved"

    # Document the security implication
    dangerous_input = "C:\\path\\"  # Trailing backslash
    result = sanitize_string(dangerous_input)

    # If this is used in a shell command like: os.system(f'echo "{result}"')
    # The backslash will escape the closing quote!
    # This is why the documentation MUST warn against shell usage.
    assert result.endswith("\\"), "Confirms trailing backslashes are preserved"


def test_dangerous_chars_are_removed():
    """Test that dangerous shell metacharacters are removed."""
    dangerous_inputs = [
        ("command;malicious", ";"),
        ("command|malicious", "|"),
        ("command&malicious", "&"),
        ("command`malicious", "`"),
        ("command$malicious", "$"),
        ("command(malicious", "("),
        ("command)malicious", ")"),
        ("command<malicious", "<"),
        ("command>malicious", ">"),
        ("command{malicious", "{"),
        ("command}malicious", "}"),
    ]

    for input_str, char in dangerous_inputs:
        result = sanitize_string(input_str)
        assert char not in result, f"Dangerous char '{char}' should be removed"


def test_sanitize_string_max_length_protection():
    """Test that input length is limited to prevent DoS."""
    # Very long input (ReDoS protection)
    long_input = "a" * 1000000
    result = sanitize_string(long_input, max_length=1000)
    assert len(result) <= 1000, "Should enforce max_length limit"


def test_sanitize_string_removes_control_characters():
    """Test that control characters are removed."""
    control_inputs = [
        ("text\nnewline", "\n"),
        ("text\ttab", "\t"),
        ("text\x00null", "\x00"),
    ]

    for input_str, char in control_inputs:
        result = sanitize_string(input_str)
        assert char not in result, f"Control char '{repr(char)}' should be removed"
