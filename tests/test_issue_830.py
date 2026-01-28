"""Test for Issue #830 - ReDoS vulnerability in fullwidth character regex.

This test verifies that the sanitize_string function properly handles
the fullwidth character regex pattern to prevent ReDoS attacks while
still correctly removing fullwidth characters.

SECURITY NOTES:
    The existing code at src/flywheel/cli.py:114-116 already implements
    the required security fix by enforcing max_length BEFORE any regex
    processing. This prevents potential ReDoS attacks through the
    fullwidth character regex pattern at line 181.

    The regex range [\uFF01-\uFF60] covers 95 fullwidth characters.
    While Python's re module handles this efficiently, enforcing the
    input length limit (max_length) before regex processing ensures
    that excessively long strings cannot cause ReDoS.
"""

import pytest
from flywheel.cli import sanitize_string


def test_fullwidth_chars_removed():
    """Test that fullwidth characters are properly removed."""
    # Test various fullwidth characters
    test_cases = [
        # Fullwidth exclamation mark to fullwidth latin letters
        ("\uFF01", ""),  # ！
        ("\uFF20", ""),  # ＠
        ("\uFF21", ""),  # Ａ
        ("\uFF41", ""),  # ａ
        ("\uFF60", ""),  # ｀

        # Mixed content
        ("Hello\uFF01World", "HelloWorld"),
        ("Test\uFF21\uFF21\uFF21", "Test"),

        # Fullwidth characters in middle of string
        ("abc\uFF01def", "abcdef"),

        # Multiple fullwidth characters
        ("\uFF01\uFF02\uFF03", ""),
    ]

    for input_str, expected in test_cases:
        result = sanitize_string(input_str)
        assert result == expected, f"Failed for input {repr(input_str)}: got {repr(result)}, expected {repr(expected)}"


def test_max_length_enforced_before_regex():
    """Test that max_length is strictly enforced before regex processing.

    This is the core security fix for Issue #830 - by enforcing the length
    limit BEFORE the regex patterns are applied, we prevent potential
    ReDoS attacks through excessively long input strings.

    The existing code at lines 114-116 of cli.py already implements this
    protection correctly.
    """
    # Create a string with normal ASCII characters
    long_string = "A" * 200000

    # Should be truncated to max_length (default 100000)
    result = sanitize_string(long_string)
    assert len(result) == 100000, f"Expected length 100000, got {len(result)}"
    assert result == "A" * 100000, "Long string should be truncated to max_length"

    # Test with custom max_length
    long_string = "B" * 50000
    result = sanitize_string(long_string, max_length=1000)
    assert len(result) == 1000, f"Expected length 1000, got {len(result)}"
    assert result == "B" * 1000, "Long string should be truncated to custom max_length"

    # Test that fullwidth chars are still removed after truncation
    long_with_fullwidth = ("A" + "\uFF21") * 60000  # 120000 chars, exceeds max_length
    result = sanitize_string(long_with_fullwidth, max_length=1000)
    # Should be truncated first, then fullwidth removed
    # First 1000 chars: 500 "A" + 500 fullwidth
    # After removing fullwidth: 500 "A"
    assert len(result) == 500, f"Expected length 500, got {len(result)}"
    assert result == "A" * 500, "Fullwidth chars should be removed after truncation"


def test_regex_complexity_with_long_input():
    """Test that regex patterns handle long input efficiently.

    This test verifies that even with a long input containing many
    fullwidth characters, the function completes quickly and correctly.
    """
    # Create a string with alternating ASCII and fullwidth characters
    # This could potentially cause catastrophic backtracking in vulnerable regex
    test_input = ("A" + "\uFF21") * 1000  # 2000 characters

    import time
    start = time.time()
    result = sanitize_string(test_input)
    elapsed = time.time() - start

    # Should complete in reasonable time (< 1 second)
    assert elapsed < 1.0, f"Regex took too long: {elapsed:.2f}s"
    assert result == "A" * 1000, f"Expected 'A' * 1000, got {repr(result)}"


def test_fullwidth_range_edge_cases():
    """Test edge cases of the fullwidth character range."""
    # Characters just outside the range
    test_cases = [
        # Before range (U+FF00)
        ("\uFF00", "\uFF00"),  # Should NOT be removed

        # After range (U+FF61)
        ("\uFF61", "\uFF61"),  # Should NOT be removed

        # Exactly at range boundaries
        ("\uFF01", ""),  # Should be removed (start of range)
        ("\uFF60", ""),  # Should be removed (end of range)
    ]

    for input_str, expected in test_cases:
        result = sanitize_string(input_str)
        assert result == expected, f"Failed for U+{ord(input_str):04X}: got {repr(result)}, expected {repr(expected)}"


def test_empty_and_edge_inputs():
    """Test empty string and edge cases."""
    assert sanitize_string("") == ""
    assert sanitize_string(None) == ""
    assert sanitize_string("   ") == "   "  # Spaces preserved
    assert sanitize_string("abc") == "abc"  # Normal ASCII preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
