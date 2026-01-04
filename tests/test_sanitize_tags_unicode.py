"""Test for sanitize_tags Unicode handling (Issue #629)."""

import pytest
from flywheel.cli import sanitize_tags


class TestSanitizeTagsUnicode:
    """Test that sanitize_tags blocks Unicode spoofing characters."""

    def test_blocks_unicode_fullwidth_characters(self):
        """Fullwidth alphanumeric characters should be removed."""
        # Fullwidth Latin capital letters (U+FF01-FF5E)
        result = sanitize_tags("ＡＢＣ")
        assert result == [], f"Expected empty list, got {result}"

    def test_blocks_unicode_cyrillic_characters(self):
        """Cyrillic characters (homoglyph attack) should be removed."""
        # Cyrillic looks like Latin but is different
        result = sanitize_tags("АВС")  # Cyrillic А, В, С
        assert result == [], f"Expected empty list, got {result}"

    def test_blocks_unicode_greek_characters(self):
        """Greek characters should be removed."""
        result = sanitize_tags("ΑΒΓ")
        assert result == [], f"Expected empty list, got {result}"

    def test_blocks_unicode_fullwidth_digits(self):
        """Fullwidth digits should be removed."""
        result = sanitize_tags("１２３")  # Fullwidth 1, 2, 3
        assert result == [], f"Expected empty list, got {result}"

    def test_blocks_zero_width_characters(self):
        """Zero-width characters should be removed."""
        result = sanitize_tags("tag\u200Btag")  # Zero-width space
        assert result == ["tagtag"], f"Expected ['tagtag'], got {result}"

    def test_allows_ascii_alphanumeric(self):
        """ASCII alphanumeric characters should be allowed."""
        result = sanitize_tags("abc123")
        assert result == ["abc123"], f"Expected ['abc123'], got {result}"

    def test_allows_ascii_with_hyphen_and_underscore(self):
        """ASCII with hyphens and underscores should be allowed."""
        result = sanitize_tags("my-tag_123")
        assert result == ["my-tag_123"], f"Expected ['my-tag_123'], got {result}"

    def test_blocks_mixed_unicode_with_ascii(self):
        """Unicode characters mixed with ASCII should have Unicode removed."""
        result = sanitize_tags("tagＡＢＣ")
        assert result == ["tag"], f"Expected ['tag'], got {result}"

    def test_blocks_unicode_in_multiple_tags(self):
        """Multiple tags with Unicode should have Unicode removed."""
        result = sanitize_tags("tag1,ＡＢＣ,tag2")
        assert result == ["tag1", "tag2"], f"Expected ['tag1', 'tag2'], got {result}"
