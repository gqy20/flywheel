"""Test for issue #751 - sanitize_tags missing individual tag length limit."""

import pytest
from flywheel.cli import sanitize_tags


def test_sanitize_tags_should_limit_individual_tag_length():
    """Test that sanitize_tags limits the length of individual tags.

    This test addresses the security issue where sanitize_tags only limits
    total input length but not individual tag length. A malicious user could
    create a single extremely long tag that could cause issues with storage
    backends or display.

    The function should truncate individual tags that exceed max_tag_length.
    """
    # Create a tag that is much longer than a reasonable limit
    long_tag = "a" * 1000  # 1000 character tag
    tags_str = f"{long_tag},normal-tag"

    # This should truncate the long tag to a reasonable length (e.g., 100 characters)
    result = sanitize_tags(tags_str)

    # The long tag should be truncated to 100 characters
    assert len(result[0]) == 100, f"Expected first tag to be truncated to 100 chars, got {len(result[0])}"
    assert result[0] == "a" * 100
    assert result[1] == "normal-tag"


def test_sanitize_tags_custom_max_tag_length():
    """Test that sanitize_tags respects custom max_tag_length parameter."""
    long_tag = "b" * 500
    tags_str = long_tag

    # Test with custom max_tag_length of 50
    result = sanitize_tags(tags_str, max_tag_length=50)

    assert len(result[0]) == 50, f"Expected tag to be truncated to 50 chars, got {len(result[0])}"
    assert result[0] == "b" * 50


def test_sanitize_tags_multiple_long_tags():
    """Test that sanitize_tags handles multiple long tags correctly."""
    tag1 = "x" * 200
    tag2 = "y" * 150
    tag3 = "z" * 300
    tags_str = f"{tag1},{tag2},{tag3}"

    # All tags should be truncated to default max_tag_length (100)
    result = sanitize_tags(tags_str)

    assert len(result) == 3
    assert len(result[0]) == 100, f"Expected tag1 to be 100 chars, got {len(result[0])}"
    assert len(result[1]) == 100, f"Expected tag2 to be 100 chars, got {len(result[1])}"
    assert len(result[2]) == 100, f"Expected tag3 to be 100 chars, got {len(result[2])}"


def test_sanitize_tags_short_tags_unchanged():
    """Test that sanitize_tags doesn't modify short tags."""
    tags_str = "short,medium-length-tag,another-tag"

    result = sanitize_tags(tags_str)

    assert result == ["short", "medium-length-tag", "another-tag"]
