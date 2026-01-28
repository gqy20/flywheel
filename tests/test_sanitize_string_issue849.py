"""Test for sanitize_string function - Issue #849

This test verifies that sanitize_string preserves spaces for display text
(titles, descriptions) rather than removing all spaces which causes data loss.

The function is used for sanitizing user-facing text (todo titles and descriptions),
NOT for generating IDs or labels. Therefore, spaces should be preserved to maintain
data integrity and readability.

The contradiction in documentation:
- Line 33 says "Removes ... All spaces ( )"
- Line 106 says "Uses separate passes ... to preserve word separation"

These are mutually exclusive - you cannot both remove all spaces AND preserve word separation.
This test fixes the contradiction by preserving spaces (the correct behavior for display text).
"""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_preserves_spaces_in_simple_text():
    """Test that spaces are preserved in simple multi-word text.

    This is the main test for Issue #849. The function currently removes
    all spaces, which causes data loss (e.g., "Hello World" becomes "HelloWorld").

    Since this function is used for display text (todo titles/descriptions),
    spaces must be preserved to maintain data integrity and readability.
    """
    # Test basic multi-word text
    assert sanitize_string("Hello World") == "Hello World"
    assert sanitize_string("Hello World Again") == "Hello World Again"


def test_sanitize_string_handles_control_chars_preserves_spaces():
    """Test that control characters are removed but spaces between words are kept.

    This verifies the "separate passes" approach mentioned in the documentation:
    - Control chars should be removed (not replaced with spaces)
    - Original spaces between words should be preserved
    """
    # Newlines and tabs should be removed, but word spaces kept
    assert sanitize_string("Hello\nWorld") == "HelloWorld"
    assert sanitize_string("Hello\tWorld") == "HelloWorld"
    assert sanitize_string("Hello\n\tWorld") == "HelloWorld"
    # Regular spaces should be preserved
    assert sanitize_string("Hello World") == "Hello World"
    # Control chars between words should just be removed (no space added)
    assert sanitize_string("Hello\n World") == "Hello World"


def test_sanitize_string_preserves_complex_text():
    """Test that spaces are preserved in more complex text with punctuation."""
    assert sanitize_string("Hello, World!") == "Hello, World!"
    assert sanitize_string("This is a test") == "This is a test"


def test_sanitize_string_removes_shell_metachars_but_keeps_spaces():
    """Test that shell metacharacters are removed while spaces are preserved."""
    # Shell metachars should be removed
    assert sanitize_string("Hello; World") == "Hello World"
    assert sanitize_string("Hello| World") == "Hello World"
    assert sanitize_string("Hello& World") == "Hello World"
    # But spaces should remain
    assert sanitize_string("Hello World") == "Hello World"


def test_sanitize_string_preserves_multiple_spaces():
    """Test that multiple spaces are preserved."""
    assert sanitize_string("Hello  World") == "Hello  World"
    assert sanitize_string("Hello   World") == "Hello   World"


def test_sanitize_string_preserves_leading_trailing_spaces():
    """Test that leading and trailing spaces are preserved."""
    assert sanitize_string(" Hello World ") == " Hello World "
    assert sanitize_string("  Hello  World  ") == "  Hello  World  "
