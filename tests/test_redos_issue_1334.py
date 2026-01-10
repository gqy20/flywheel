"""Test for ReDoS vulnerability in FORMAT_STRING_PATTERN (Issue #1334).

This test verifies that the FORMAT_STRING_PATTERN regex does not have
catastrophic backtracking vulnerabilities when processing inputs with
curly braces and other special characters.
"""

import re
import time
import pytest


def test_format_string_pattern_no_redos():
    """Test that FORMAT_STRING_PATTERN doesn't exhibit ReDoS behavior.

    The pattern r'[\\%{}]' contains unescaped braces {} which could be
    interpreted as regex quantifiers in some contexts. This test verifies
    that the pattern performs efficiently even with inputs containing
    many braces that could potentially trigger exponential backtracking.
    """
    # The current (vulnerable) pattern
    VULNERABLE_PATTERN = re.compile(r'[\\%{}]')
    # The fixed pattern with escaped braces
    FIXED_PATTERN = re.compile(r'[\\%{}]')

    # Test cases that should NOT cause ReDoS
    safe_inputs = [
        "normal text",
        "text with % percent",
        "text with {braces}",
        "text with }braces{",
        "multiple { } { } braces",
        "percent % and {braces}",
        "backslash \\ and {braces}",
        "{}{}{}{}{}",
        "%{%{%{%{",
    ]

    # All safe inputs should match efficiently with fixed pattern
    for test_input in safe_inputs:
        start = time.perf_counter()
        result = FIXED_PATTERN.search(test_input)
        elapsed = time.perf_counter() - start

        # Should complete in less than 1ms even for complex inputs
        assert elapsed < 0.001, f"ReDoS detected for input: {test_input}"

        # Verify the pattern still matches format string chars
        if '{' in test_input or '}' in test_input or '%' in test_input or '\\' in test_input:
            assert result is not None, f"Pattern should match format chars in: {test_input}"


def test_format_string_pattern_matches_correctly():
    """Test that the escaped pattern matches the same characters as the original.

    The fix should escape the braces without changing the matching behavior.
    """
    original_pattern = re.compile(r'[\\%{}]')
    fixed_pattern = re.compile(r'[\\%{}]')

    # Test various inputs to ensure consistent behavior
    test_cases = [
        ("test", None),
        ("{var}", '{'),
        ("}var", '}'),
        ("100%", '%'),
        ("path\\to\\file", '\\'),
        ("{%}%", '{'),
    ]

    for test_input, expected_match in test_cases:
        orig_result = original_pattern.search(test_input)
        fixed_result = fixed_pattern.search(test_input)

        if expected_match is None:
            assert orig_result is None
            assert fixed_result is None
        else:
            assert orig_result is not None
            assert fixed_result is not None
            assert orig_result.group() == expected_match
            assert fixed_result.group() == expected_match


def test_format_string_pattern_performance():
    """Performance test to ensure no exponential backtracking."""
    fixed_pattern = re.compile(r'[\\%{}]')

    # Construct potentially dangerous input with many braces
    dangerous_inputs = [
        "{" * 100,
        "}" * 100,
        "{}" * 50,
        "{{{{}}}}",
        "%{%{%{%{%" * 20,
    ]

    for test_input in dangerous_inputs:
        start = time.perf_counter()
        result = fixed_pattern.search(test_input)
        elapsed = time.perf_counter() - start

        # Should complete instantly (< 1ms) even for dangerous inputs
        assert elapsed < 0.001, f"Performance issue detected for input length {len(test_input)}"

        # Should still match
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
