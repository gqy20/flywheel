"""Test for sanitize_string return statement (Issue #866)."""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_returns_value():
    """Test that sanitize_string returns the sanitized string, not None."""
    # Test basic functionality
    result = sanitize_string("Hello World")
    assert result is not None, "sanitize_string should return a value, not None"
    assert result == "Hello World", f"Expected 'Hello World', got '{result}'"

    # Test with control characters
    result = sanitize_string("test\x00extra")
    assert result is not None, "sanitize_string should return a value, not None"
    assert result == "testextra", f"Expected 'testextra', got '{result}'"

    # Test with metacharacters
    result = sanitize_string("test;command")
    assert result is not None, "sanitize_string should return a value, not None"
    assert result == "testcommand", f"Expected 'testcommand', got '{result}'"

    # Test with max_length parameter
    long_string = "a" * 200000
    result = sanitize_string(long_string, max_length=1000)
    assert result is not None, "sanitize_string should return a value, not None"
    assert len(result) == 1000, f"Expected length 1000, got {len(result)}"
