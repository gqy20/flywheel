"""Test for control character replacement security warning (Issue #819)."""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_warns_about_control_char_space_risk():
    """Test that sanitize_string documents control character space replacement risk.

    Issue #819: Control characters (newlines, tabs, etc.) are replaced with spaces
    to prevent word concatenation. However, if the sanitized string is used in
    unsafe shell contexts (e.g., unquoted arguments), these spaces could be
    exploited for argument injection.

    This test verifies that the function's documentation explicitly warns about:
    1. Control characters being replaced with spaces
    2. The risk of using the output in shell commands without proper quoting
    3. The need for parameterized queries or proper quoting
    """
    docstring = sanitize_string.__doc__

    # Verify the docstring exists
    assert docstring is not None, "Function must have documentation"

    docstring_lower = docstring.lower()

    # Check for explicit warnings about control character space replacement
    security_keywords = [
        "control character",
        "space",
        "shell",
        "injection",
        "parameterized",
        "quot",
    ]

    found_warnings = [keyword for keyword in security_keywords if keyword in docstring_lower]

    # Should have at least 3 of these security-related terms
    assert len(found_warnings) >= 3, (
        f"Docstring must warn about control character space replacement risks. "
        f"Found keywords: {found_warnings}. "
        f"Should include warnings about control characters, spaces, shell injection, "
        f"and the need for parameterized queries or proper quoting."
    )

    # Specifically mention that control characters are replaced with spaces
    assert any(
        term in docstring_lower for term in ["control character", "newline", "tab"]
    ), "Docstring must mention control characters (newlines, tabs, etc.)"

    assert "space" in docstring_lower, (
        "Docstring must mention that control characters are replaced with spaces"
    )

    # Mention shell command risks
    assert any(
        term in docstring_lower for term in ["shell command", "os.system", "subprocess", "unquoted"]
    ), "Docstring must explicitly warn against using output in shell commands without proper quoting"

    # Mention safe alternatives
    assert any(
        term in docstring_lower for term in ["parameterized", "shlex.quote", "shell=false"]
    ), "Docstring must recommend safe alternatives (parameterized queries, shlex.quote(), or subprocess with shell=False)"


def test_control_character_replaced_with_space():
    """Test that control characters are replaced with spaces (current behavior).

    This test documents the current behavior where control characters are
    replaced with spaces to prevent word concatenation issues.

    Security Note: While this prevents word concatenation (e.g., 'Hello\nWorld'
    becoming 'HelloWorld'), it introduces a different risk: if this sanitized
    string is used in shell commands without proper quoting, the spaces could
    be exploited for argument injection.

    Example of the risk:
        input: "todo\x00extra args"
        sanitized: "todo extra args"
        dangerous: os.system(f'echo {sanitized}')  # No quoting!
        result: echo todo extra args  # Argument injection!

    The fix is to ensure the output is ALWAYS properly quoted when used in
    shell commands: os.system(f'echo "{sanitized}"') or better yet, use
    subprocess with list arguments: subprocess.run(['echo', sanitized]).
    """
    # Test that control characters are replaced with spaces
    test_cases = [
        ("Hello\nWorld", "Hello World"),  # newline -> space
        ("Hello\tWorld", "Hello World"),  # tab -> space
        ("Hello\x00World", "Hello World"),  # null -> space
        ("Line1\r\nLine2", "Line1  Line2"),  # CRLF -> 2 spaces
        ("text\x1Bmore", "text more"),  # escape -> space
    ]

    for input_str, expected in test_cases:
        result = sanitize_string(input_str)
        # After sanitization, control chars should become spaces
        # We verify by checking no control characters remain
        for codepoint in range(32):  # 0-31 are control characters
            control_char = chr(codepoint)
            assert control_char not in result, (
                f"Control character {repr(control_char)} (code {codepoint}) "
                f"should be replaced, found in: {repr(result)}"
            )

        # And verify word separation is preserved (not concatenated)
        if "\n" in input_str or "\t" in input_str or "\x00" in input_str:
            # Should have space between the words
            assert " " in result, (
                f"Word separation should be preserved for input {repr(input_str)}, "
                f"got {repr(result)}"
            )


def test_sanitize_string_not_for_shell_safety():
    """Test that documentation explicitly states function is not for shell safety.

    Issue #819: The function replaces control characters with spaces. If used
    in shell commands without proper quoting, this could enable argument injection.
    The documentation must be crystal clear that this function is NOT for shell
    safety and should not be used as such.
    """
    docstring = sanitize_string.__doc__
    docstring_lower = docstring.lower()

    # Should explicitly state it's NOT for shell safety
    assert any(
        phrase in docstring_lower for phrase in [
            "not suitable for shell",
            "not for shell",
            "does not provide shell",
            "should not be used for shell",
        ]
    ), "Documentation must explicitly state this function is NOT for shell injection prevention"

    # Should mention the warning in all caps or emphasized
    assert "warning" in docstring_lower, (
        "Documentation should contain WARNING about shell safety"
    )
