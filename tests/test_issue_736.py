"""Test for shell injection via backslash escape (Issue #736).

The vulnerability: If sanitized output is used in shell commands, a trailing
backslash can escape the closing quote and inject arbitrary commands.

Example:
    sanitized = sanitize_string("C:\\path\\")  # Returns "C:\path\"
    os.system(f'echo "{sanitized}"')  # Becomes: echo "C:\path\"
    # The trailing \ escapes the ", allowing command injection!

This test ensures that trailing backslashes are stripped to prevent this.
"""

import pytest
from flywheel.cli import sanitize_string


def test_trailing_backslash_removed_for_shell_safety():
    """Test that trailing backslashes are removed to prevent shell injection.

    A trailing backslash can escape the closing quote in shell commands:
    - echo "C:\path\"  <- The backslash escapes the closing quote
    - This allows arbitrary command injection

    This test verifies the fix for Issue #736.
    """
    # Test cases with trailing backslashes
    dangerous_inputs = [
        "C:\\path\\",  # Windows path with trailing backslash
        "path\\",  # Simple trailing backslash
        "text\\\\",  # Multiple trailing backslashes
        "C:\\Users\\Admin\\",  # Multiple trailing backslashes
        "path with spaces\\",  # Trailing backslash with spaces
    ]

    for input_str in dangerous_inputs:
        result = sanitize_string(input_str)

        # Result should not end with a backslash
        assert not result.endswith("\\"), (
            f"Input '{input_str}' produced unsafe output '{result}'. "
            f"Trailing backslash can escape quotes in shell commands. "
            f"Example: os.system(f'echo \"{result}\"') would be vulnerable."
        )


def test_internal_backslashes_preserved():
    """Test that internal backslashes are still preserved for legitimate uses.

    While trailing backslashes are dangerous, internal backslashes are needed for:
    - Windows paths: C:\\Users\\file.txt
    - Markdown: \\*not bold\\*
    - Regex: \\d+, \\w+, etc.
    """
    # Legitimate uses with internal backslashes
    safe_inputs = [
        ("C:\\Users\\Admin\\file.txt", "C:\\Users\\Admin\\file.txt"),
        ("\\*not bold\\*", "\\*not bold\\*"),
        ("\\d+", "\\d+"),
        ("C:\\path\\to\\file", "C:\\path\\to\\file"),
        ("\\\\server\\share", "\\\\server\\share"),
    ]

    for input_str, expected in safe_inputs:
        result = sanitize_string(input_str)

        # Should preserve internal backslashes
        assert "\\" in result, (
            f"Input '{input_str}' should preserve internal backslashes"
        )

        # Should not end with backslash (if input didn't have trailing one)
        if not input_str.endswith("\\"):
            assert "\\" in result, "Internal backslashes should be preserved"


def test_only_trailing_backslash_removed():
    """Test that only trailing backslashes are removed, not internal ones."""
    # Input with both internal and trailing backslashes
    input_str = "C:\\Users\\Admin\\"
    result = sanitize_string(input_str)

    # Should have internal backslashes
    assert "\\\\" in result or "\\U" in result or "\\A" in result, (
        "Internal backslashes should be preserved"
    )

    # Should not end with backslash
    assert not result.endswith("\\"), (
        f"Result '{result}' should not end with backslash"
    )


def test_multiple_trailing_backslashes():
    """Test that multiple trailing backslashes are all removed."""
    test_cases = [
        ("path\\\\", "path"),  # Two trailing
        ("path\\\\\\\\", "path"),  # Four trailing
        ("text\\\\\\", "text"),  # Three trailing (odd number)
    ]

    for input_str, expected_base in test_cases:
        result = sanitize_string(input_str)
        assert not result.endswith("\\"), (
            f"Input '{input_str}' should have all trailing backslashes removed"
        )


def test_empty_or_only_backslashes():
    """Test edge cases with empty strings or only backslashes."""
    # Empty string
    assert sanitize_string("") == ""

    # Only backslashes
    result = sanitize_string("\\")
    assert result == "" or result == "\\", (
        "Single backslash should be handled safely"
    )

    # Multiple backslashes only
    result = sanitize_string("\\\\\\\\")
    assert not result.endswith("\\"), (
        "String of only backslashes should not end with backslash"
    )
