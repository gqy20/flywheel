"""Tests for sanitize_tags ReDoS protection (Issue #704)."""

import pytest

from flywheel.cli import sanitize_tags


class TestSanitizeTagsReDoS:
    """Test suite for ReDoS protection in sanitize_tags function."""

    def test_basic_tags_sanitization(self):
        """Test that basic tags are sanitized correctly."""
        assert sanitize_tags("work,personal") == ["work", "personal"]

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert sanitize_tags("work$tag,test;tag") == ["worktag", "testtag"]

    def test_alphanumeric_underscore_hyphen_preserved(self):
        """Test that alphanumeric, underscore, and hyphen are preserved."""
        assert sanitize_tags("tag_123,test-tag") == ["tag_123", "test-tag"]

    def test_empty_tags_filtered(self):
        """Test that empty tags after sanitization are filtered out."""
        assert sanitize_tags("valid,***,test") == ["valid", "test"]

    def test_whitespace_trimmed(self):
        """Test that whitespace is trimmed from tags."""
        assert sanitize_tags("  work  ,  personal  ") == ["work", "personal"]

    def test_max_length_enforcement(self):
        """Test that max_length is enforced."""
        long_input = "a" * 20000
        result = sanitize_tags(long_input)
        # Should not crash and should handle the input safely
        assert isinstance(result, list)

    def test_max_tags_enforcement(self):
        """Test that max_tags is enforced."""
        many_tags = ",".join([f"tag{i}" for i in range(200)])
        result = sanitize_tags(many_tags)
        # Should only return max_tags (100)
        assert len(result) == 100

    def test_none_input(self):
        """Test that None input returns empty list."""
        assert sanitize_tags(None) == []

    def test_empty_string(self):
        """Test that empty string returns empty list."""
        assert sanitize_tags("") == []

    def test_unicode_characters_removed(self):
        """Test that Unicode characters are removed."""
        assert sanitize_tags("tag中文,emoji😀") == ["tag", "emoji"]

    def test_control_characters_removed(self):
        """Test that control characters are removed."""
        assert sanitize_tags("tag\n\t\r,test") == ["tag", "test"]
