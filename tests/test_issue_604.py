"""Test for sanitize_tags Unicode spoofing and control characters (Issue #604)."""

import pytest
from flywheel.cli import sanitize_tags


class TestSanitizeTagsUnicode:
    """Test sanitize_tags handles Unicode spoofing and control characters."""

    def test_fullwidth_characters_removed(self):
        """Fullwidth characters should be removed."""
        # Fullwidth alphanumeric characters (U+FF01-FF60)
        result = sanitize_tags("fullwidth")
        assert result == ["fullwidth"]

    def test_control_characters_removed(self):
        """Control characters should be removed."""
        # Various control characters
        result = sanitize_tags("test\x00\x01\x02\x1F")
        assert result == ["test"]

    def test_malicious_unicode_homoglyphs_removed(self):
        """Malicious Unicode homoglyphs should be removed."""
        # Cyrillic letters that look like Latin
        result = sanitize_tags("malicious")
        assert result == ["malicious"]

    def test_whitespace_variations_normalized(self):
        """Various whitespace characters should be handled."""
        # Non-breaking spaces, em spaces, en spaces, etc.
        result = sanitize_tags("tag with\u2003spaces")
        # Should handle various Unicode whitespace
        assert len(result) >= 1
        assert all(tag for tag in result)

    def test_right_to_left_override_removed(self):
        """Bidirectional override characters should be removed."""
        result = sanitize_tags("test\u202Etag")
        # RTL override should be stripped
        assert "tag" in result[0] or result == ["testtag"]

    def test_zero_width_characters_removed(self):
        """Zero-width characters should be removed."""
        result = sanitize_tags("test\u200B\u200C\u200Dtag")
        # Zero-width characters should be stripped
        assert result == ["testtag"]

    def test_valid_tags_pass(self):
        """Valid tags with allowed characters should pass."""
        result = sanitize_tags("valid-tag, valid_tag, validtag123")
        assert result == ["valid-tag", "valid_tag", "validtag123"]

    def test_mixed_valid_invalid(self):
        """Mix of valid tags and tags with Unicode issues."""
        result = sanitize_tags("good-tag,bad\u200Btag,another-good")
        # Should include valid tags and sanitize bad ones
        assert "good-tag" in result
        assert "another-good" in result

    def test_empty_after_sanitization(self):
        """Tags that become empty after sanitization should be dropped."""
        result = sanitize_tags("\x00\x01\x02")
        assert result == []

    def test_emoji_and_symbols_removed(self):
        """Emoji and symbols should be removed from tags."""
        result = sanitize_tags("test😀tag")
        # Emoji should be stripped, leaving test and tag
        assert "test" in result[0]
        assert "tag" in result[0]
