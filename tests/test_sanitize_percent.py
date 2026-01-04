"""Test for percent sign filtering in sanitize_string (Issue #640)."""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_removes_percent_sign():
    """Test that sanitize_string removes percent signs to prevent format string attacks."""
    # Test single percent sign
    assert sanitize_string("test%") == "test"
    assert sanitize_string("%test") == "test"
    assert sanitize_string("te%st") == "test"

    # Test multiple percent signs
    assert sanitize_string("test%%string") == "teststring"
    assert sanitize_string("100% complete") == "100 complete"

    # Test percent signs with other dangerous characters
    assert sanitize_string("test%$string") == "teststring"
    assert sanitize_string("%s%s%s") == "sss"

    # Test format string patterns
    assert sanitize_string("%s %d %f") == "s d f"
    assert sanitize_string("Price: %d%%") == "Price: d"

    # Test that percent signs are removed even in complex strings
    assert sanitize_string("Task: Complete %50% of work") == "Task: Complete 50 of work"


def test_sanitize_string_preserves_safe_characters():
    """Test that sanitize_string still preserves safe characters."""
    assert sanitize_string("Hello World!") == "Hello World!"
    assert sanitize_string("Test, with: punctuation.") == "Test, with: punctuation."
    assert sanitize_string("user-name_123") == "user-name_123"
