"""Tests for sanitize_tags function - Issue #689

Tests that sanitize_tags properly validates tag format to prevent:
- Tags starting with hyphens
- Tags ending with hyphens
- Tags with consecutive hyphens
"""

import pytest
from flywheel.cli import sanitize_tags


class TestSanitizeTagsHyphenValidation:
    """Test suite for Issue #689 - Hyphen validation in sanitize_tags."""

    def test_reject_tag_starting_with_hyphen(self):
        """Tags should not start with a hyphen."""
        result = sanitize_tags("-invalid")
        assert result == [], f"Expected empty list, got {result}"

    def test_reject_tag_ending_with_hyphen(self):
        """Tags should not end with a hyphen."""
        result = sanitize_tags("invalid-")
        assert result == [], f"Expected empty list, got {result}"

    def test_reject_tag_with_consecutive_hyphens(self):
        """Tags should not contain consecutive hyphens."""
        result = sanitize_tags("in--valid")
        assert result == [], f"Expected empty list, got {result}"

    def test_reject_multiple_consecutive_hyphens(self):
        """Tags should not contain multiple consecutive hyphens."""
        result = sanitize_tags("in---valid")
        assert result == [], f"Expected empty list, got {result}"

    def test_reject_tag_starting_and_ending_with_hyphen(self):
        """Tags should not start and end with hyphens."""
        result = sanitize_tags("-invalid-")
        assert result == [], f"Expected empty list, got {result}"

    def test_accept_valid_tag_with_internal_hyphen(self):
        """Valid tags with internal hyphens should be accepted."""
        result = sanitize_tags("valid-tag")
        assert result == ["valid-tag"], f"Expected ['valid-tag'], got {result}"

    def test_accept_valid_tag_with_multiple_internal_hyphens(self):
        """Valid tags with multiple internal hyphens should be accepted."""
        result = sanitize_tags("my-valid-tag")
        assert result == ["my-valid-tag"], f"Expected ['my-valid-tag'], got {result}"

    def test_mixed_valid_and_invalid_tags(self):
        """Mixed input should only keep valid tags."""
        result = sanitize_tags("valid-tag, -invalid, in--valid, good-tag")
        assert result == ["valid-tag", "good-tag"], f"Expected ['valid-tag', 'good-tag'], got {result}"

    def test_empty_and_hyphen_only_tags(self):
        """Empty tags and hyphen-only tags should be rejected."""
        result = sanitize_tags("-, --, ---")
        assert result == [], f"Expected empty list, got {result}"

    def test_valid_tags_with_underscore_and_numbers(self):
        """Valid tags with underscores and numbers should be accepted."""
        result = sanitize_tags("tag_1, tag-2, tag_3-4")
        assert result == ["tag_1", "tag-2", "tag_3-4"], f"Expected ['tag_1', 'tag-2', 'tag_3-4'], got {result}"
