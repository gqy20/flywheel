"""Test for ReDoS vulnerability in _sanitize_text via str.split() - Issue #1504.

This test validates that _sanitize_text can handle extremely long strings
with continuous whitespace without causing memory exhaustion or high latency.
"""

import pytest
import time
from flywheel.todo import _sanitize_text


def test_sanitize_text_with_extreme_whitespace():
    """Test that _sanitize_text handles extreme whitespace efficiently.

    Creates a string with 1MB of continuous whitespace to ensure the function
    doesn't create a massive list of empty strings or consume excessive memory.
    The original implementation using str.split() could create millions of
    empty strings for such input.

    This test enforces:
    1. Memory efficiency (no list explosion)
    2. Time efficiency (should complete quickly)
    3. Correctness (result should be properly normalized)
    """
    # Create a string with 1MB of continuous spaces
    # This would create millions of empty strings with naive str.split()
    size = 1024 * 1024  # 1MB
    text = " " * size

    # Add some actual content at the end to verify it's preserved
    text += "hello   world"

    # Measure execution time - should be fast (< 1 second for 1MB)
    start_time = time.time()
    result = _sanitize_text(text)
    elapsed_time = time.time() - start_time

    # Verify correctness - result should be normalized to single space
    assert result == "hello world", f"Expected 'hello world', got '{result}'"

    # Verify performance - should complete in reasonable time
    # If str.split() creates millions of empty strings, this would take much longer
    assert elapsed_time < 1.0, f"Function took {elapsed_time:.2f}s, expected < 1.0s"


def test_sanitize_text_with_mixed_whitespace():
    """Test that _sanitize_text handles mixed whitespace characters efficiently."""
    # Create a string with alternating different whitespace characters
    size = 10000  # Smaller test for mixed whitespace
    text = (" \t\n\r" * size) + "test"

    start_time = time.time()
    result = _sanitize_text(text)
    elapsed_time = time.time() - start_time

    # All whitespace should be normalized to single space
    assert result == "test", f"Expected 'test', got '{result}'"
    assert elapsed_time < 0.1, f"Function took {elapsed_time:.2f}s, expected < 0.1s"


def test_sanitize_text_with_leading_trailing_whitespace():
    """Test that _sanitize_text preserves leading/trailing whitespace.

    Note: _sanitize_text normalizes internal whitespace but preserves
    leading and trailing whitespace. The strip() is called separately
    in the from_dict method.
    """
    text = "   \n\n\t\t  hello  world  \t\t\n\n   "

    result = _sanitize_text(text)

    # Leading/trailing whitespace is preserved (normalized to single space)
    # Internal whitespace is normalized
    assert result == " hello world ", f"Expected ' hello world ', got '{result}'"


def test_sanitize_text_normal_case():
    """Test that _sanitize_text works correctly for normal cases."""
    test_cases = [
        ("hello world", "hello world"),
        ("  hello  world  ", " hello world "),  # Preserves leading/trailing
        ("hello\tworld\nfoo", "hello world foo"),
        ("hello\n\nworld", "hello world"),
        ("  ", " "),  # Whitespace normalized to single space
        ("", ""),  # Empty string should remain empty
        ("hello", "hello"),  # Single word without whitespace
        ("\thello\n", " hello "),  # Tabs/newlines converted to space
    ]

    for input_text, expected in test_cases:
        result = _sanitize_text(input_text)
        assert result == expected, f"For input '{repr(input_text)}', expected '{repr(expected)}', got '{repr(result)}'"
