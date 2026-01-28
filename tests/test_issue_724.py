"""Test for Issue #724 - Regex hyphen position in character class."""

import pytest

from flywheel.cli import sanitize_string


def test_sanitize_string_removes_shell_metacharacters():
    """Test that sanitize_string removes dangerous shell metacharacters."""
    # Test basic shell metacharacters
    assert sanitize_string("test;cmd") == "testcmd"
    assert sanitize_string("test|pipe") == "testpipe"
    assert sanitize_string("test&amp") == "testamp"
    assert sanitize_string("test`backtick") == "testbacktick"
    assert sanitize_string("test$dollar") == "testdollar"
    assert sanitize_string("test(paren)") == "testparen"
    assert sanitize_string("test<less>") == "testless"
    assert sanitize_string("test{brace}") == "testbrace"


def test_sanitize_string_preserves_hyphens():
    """Test that sanitize_string preserves hyphens in legitimate contexts.

    This test ensures that the regex pattern correctly handles hyphens
    by placing them at the end of the character class, not in the middle
    where they would be interpreted as range operators.

    Addresses Issue #724 - Hyphen should not be removed as it's needed for:
    - UUIDs (550e8400-e29b-41d4-a716-446655440000)
    - Hyphenated words (well-known, self-contained)
    - ISO dates (2024-01-15)
    - Phone numbers (1-800-555-0123)
    - URLs and file paths
    """
    # UUID with hyphens
    assert sanitize_string("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

    # Hyphenated words
    assert sanitize_string("well-known self-contained") == "well-known self-contained"

    # ISO dates
    assert sanitize_string("2024-01-15") == "2024-01-15"

    # Phone numbers
    assert sanitize_string("1-800-555-0123") == "1-800-555-0123"

    # File paths
    assert sanitize_string("C:\\Users\\test-file") == "C:\\Users\\test-file"

    # URLs
    assert sanitize_string("https://example.com/test-file") == "https://example.com/test-file"


def test_sanitize_string_combination():
    """Test sanitize_string with combination of dangerous and safe characters."""
    # Test that dangerous chars are removed but hyphens are preserved
    input_str = "test;cmd-with-uuid:550e8400-e29b`backtick"
    expected = "testcmd-with-uuid550e8400-e29bbacktick"
    assert sanitize_string(input_str) == expected

    # Test with shell injection attempt containing hyphens
    input_str = "rm -rf /path/to-file"
    expected = "rm -rf pathto-file"  # ; and / removed, but - preserved
    result = sanitize_string(input_str)
    assert result == expected


def test_sanitize_string_hyphen_not_in_range():
    """Test that hyphen in regex is not interpreted as range operator.

    If the hyphen is incorrectly positioned in the middle of the character class
    (e.g., [{}-]), it would create a range from '}' to '-', which could cause
    unexpected character removal. This test verifies that the hyphen is properly
    positioned at the end of the character class.
    """
    # Test characters that might be in a malformed range
    # If {}- is interpreted as a range, unexpected behavior would occur
    assert sanitize_string("test{value}-dash") == "testvaluedash"

    # Test that all ASCII characters between } and - (if range was created)
    # are NOT unintentionally removed
    # The range } to - would include: } ~ ( DEL if going backwards)
    # This shouldn't happen with correct regex syntax
    assert sanitize_string("test~value") == "test~value"
