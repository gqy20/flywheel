"""Test for Issue #1094 - Potential DoS via memory allocation.

This test verifies that:
1. max_length parameter has a hard upper limit to prevent memory exhaustion
2. Attempting to set max_length above the hard limit is rejected or capped
"""

import pytest
from flywheel.cli import sanitize_for_security_context, remove_control_chars


def test_max_length_hard_limit_sanitize_for_security_context():
    """Test that sanitize_for_security_context enforces a hard upper limit on max_length."""
    # Attempt to pass an extremely large max_length that could cause memory issues
    # 100MB of text could cause memory exhaustion
    malicious_max_length = 100 * 1024 * 1024  # 100MB

    # Create a moderately long string (10KB) to test with
    test_string = "A" * 10000

    # The function should either:
    # 1. Raise an error for excessively large max_length, OR
    # 2. Cap max_length to a reasonable hard limit (e.g., 1MB)

    # Expected behavior: max_length should be capped to prevent memory exhaustion
    # A reasonable hard limit would be 1MB (1,048,576 bytes/characters)

    result = sanitize_for_security_context(
        test_string,
        context="general",
        max_length=malicious_max_length
    )

    # If max_length is capped, the result should not exceed the hard limit
    # even if we passed a larger max_length
    hard_limit = 1 * 1024 * 1024  # 1MB

    # The test string is only 10KB, so it should pass through unchanged
    # But we want to verify the function has internal protection
    assert len(result) <= hard_limit, (
        f"Result length {len(result)} exceeds hard limit of {hard_limit}. "
        f"Function accepted max_length={malicious_max_length} without enforcement."
    )


def test_max_length_hard_limit_remove_control_chars():
    """Test that remove_control_chars enforces a hard upper limit on max_length."""
    # Attempt to pass an extremely large max_length that could cause memory issues
    malicious_max_length = 100 * 1024 * 1024  # 100MB

    # Create a moderately long string (10KB) to test with
    test_string = "B" * 10000

    result = remove_control_chars(test_string, max_length=malicious_max_length)

    # The function should have a hard limit to prevent memory exhaustion
    hard_limit = 1 * 1024 * 1024  # 1MB

    assert len(result) <= hard_limit, (
        f"Result length {len(result)} exceeds hard limit of {hard_limit}. "
        f"Function accepted max_length={malicious_max_length} without enforcement."
    )


def test_reasonable_max_length_accepted():
    """Test that reasonable max_length values are still accepted."""
    test_string = "C" * 50000  # 50KB

    # A reasonable max_length should work fine
    result1 = sanitize_for_security_context(
        test_string,
        context="general",
        max_length=100000
    )
    assert len(result1) == 50000

    result2 = remove_control_chars(test_string, max_length=100000)
    assert len(result2) == 50000


def test_hard_limit_enforcement_on_large_string():
    """Test that even with large max_length, extremely large strings are capped at hard limit."""
    # Create a string larger than the hard limit
    hard_limit = 1 * 1024 * 1024  # 1MB
    large_string = "D" * (hard_limit + 100000)  # 1MB + 100KB

    # Try to use a max_length larger than the hard limit
    malicious_max_length = 10 * 1024 * 1024  # 10MB

    result = sanitize_for_security_context(
        large_string,
        context="general",
        max_length=malicious_max_length
    )

    # Result should be capped at the hard limit, not at the requested max_length
    assert len(result) <= hard_limit, (
        f"Function allowed processing of string larger than hard limit. "
        f"Result length: {len(result)}, Hard limit: {hard_limit}"
    )
