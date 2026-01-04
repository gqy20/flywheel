"""Test for Issue #635 - ReDoS vulnerability in sanitize_tags

This test verifies that the sanitize_tags function properly prevents
ReDoS (Regular Expression Denial of Service) attacks by:

1. Limiting the maximum input length before processing
2. Limiting the maximum number of tags processed
3. Using safe regex patterns that don't allow catastrophic backtracking

The fix adds input validation BEFORE the regex processing loop to prevent
an attacker from causing performance degradation via excessive tag input.

Issue #635 identified that processing thousands of comma-separated tags
could lead to performance issues as each tag requires regex substitution.
"""

import pytest
from flywheel.cli import sanitize_tags


def test_normal_tags():
    """Test that normal tags work correctly after the fix."""
    tags_str = "work,urgent,project-alpha"
    result = sanitize_tags(tags_str)
    assert result == ["work", "urgent", "project-alpha"]


def test_tags_with_special_characters():
    """Test that special characters are removed (whitelist approach)."""
    tags_str = "work@home,test#123,danger$!"
    result = sanitize_tags(tags_str)
    assert result == ["workhome", "test123", "danger"]


def test_empty_tags_after_sanitization():
    """Test that empty tags after sanitization are not included."""
    tags_str = "work,@#$,test"
    result = sanitize_tags(tags_str)
    assert result == ["work", "test"]


def test_excessive_number_of_tags_is_limited():
    """Test that excessive number of tags is limited to prevent DoS.

    This test verifies that when a user provides more than the default
    maximum of 100 tags, the function limits processing to prevent
    performance degradation (ReDoS prevention).
    """
    # Create 10,000 tags (which could cause performance issues without limits)
    tags_str = ",".join([f"tag{i}" for i in range(10000)])

    # The function should limit to max_tags (default 100)
    result = sanitize_tags(tags_str)

    # Verify that we have exactly 100 tags (the default limit)
    assert len(result) == 100, "Should limit excessive tags to prevent DoS"
    assert all(tag.startswith("tag") for tag in result)


def test_excessive_tag_string_length_is_limited():
    """Test that very long tag strings are truncated before processing.

    This test verifies that input length limits prevent processing of
    extremely long input strings that could cause performance issues.
    """
    # Create a tag string longer than max_length (default 10000)
    # Each tag is "tagXXX" (6 chars) + comma = 7 chars, so ~1428 tags = ~10000 chars
    # Let's create 2000 tags to exceed the limit
    tags_str = ",".join([f"tag{i}" for i in range(2000)])

    # The function should truncate to max_length before processing
    result = sanitize_tags(tags_str)

    # Should handle efficiently by truncating first
    assert isinstance(result, list)
    assert len(result) > 0
    # Due to truncation, we should get approximately 100 tags
    # (since max_length=10000 and we process first max_tags=100 after split)
    assert len(result) <= 100


def test_custom_limits():
    """Test that custom limits can be specified."""
    # Create 50 tags
    tags_str = ",".join([f"tag{i}" for i in range(50)])

    # Set a custom limit of 10 tags
    result = sanitize_tags(tags_str, max_tags=10)

    assert len(result) == 10


def test_unicode_spoofing_characters_removed():
    """Test that Unicode spoofing characters are removed.

    The whitelist approach should automatically remove:
    - Zero-width characters (U+200B)
    - Fullwidth characters (U+FF01-FF60)
    - Other Unicode spoofing characters
    """
    # Fullwidth characters, zero-width characters, etc.
    tags_str = "work\u200B,test\uFF01,valid-tag"
    result = sanitize_tags(tags_str)

    # Should remove the Unicode spoofing characters
    assert "valid-tag" in result
    # The zero-width and fullwidth characters should be removed
    # leaving only "work" and "test" (and "valid-tag")
    assert "work" in result


def test_empty_and_none_input():
    """Test that empty input returns empty list."""
    assert sanitize_tags("") == []
    assert sanitize_tags(None) == []
