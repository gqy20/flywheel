"""Test for issue #1645 - Incomplete invisible character sanitization.

This test verifies that _sanitize_text properly removes all invisible Unicode
characters, not just the basic zero-width spaces.
"""

import pytest
from flywheel.todo import _sanitize_text


class TestInvisibleCharacterSanitization:
    """Test comprehensive invisible character removal."""

    def test_soft_hyphen_is_removed(self):
        """Soft Hyphen (U+00AD) should be removed."""
        # Soft Hyphen is an invisible character that can be used for attacks
        text = "hello\u00ADworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\u00AD" not in result

    def test_combining_grapheme_joiner_is_removed(self):
        """Combining Grapheme Joiner (U+034F) should be removed."""
        text = "hello\u034Fworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\u034F" not in result

    def test_zero_width_space_is_removed(self):
        """Zero Width Space (U+200B) should be removed."""
        text = "hello\u200Bworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\u200B" not in result

    def test_zero_width_non_joiner_is_removed(self):
        """Zero Width Non-Joiner (U+200C) should be removed."""
        text = "hello\u200Cworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\u200C" not in result

    def test_zero_width_joiner_is_removed(self):
        """Zero Width Joiner (U+200D) should be removed."""
        text = "hello\u200Dworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\u200D" not in result

    def test_word_joiner_is_removed(self):
        """Word Joiner (U+2060) should be removed."""
        text = "hello\u2060world"
        result = _sanitize_text(text)
        assert result == "hello space"
        assert "\u2060" not in result

    def test_zero_width_no_break_space_is_removed(self):
        """Zero Width No-Break Space (U+FEFF) should be removed."""
        text = "hello\uFEFFworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        assert "\uFEFF" not in result

    def test_multiple_invisible_chars_removed(self):
        """Multiple different invisible characters should all be removed."""
        # Combination of various invisible characters
        text = "hello\u00AD\u200B\u200C\u200D\u034F\u2060\uFEFFworld"
        result = _sanitize_text(text)
        assert result == "hello world"
        # Ensure none of the invisible chars remain
        invisible_chars = ["\u00AD", "\u200B", "\u200C", "\u200D", "\u034F", "\u2060", "\uFEFF"]
        for char in invisible_chars:
            assert char not in result

    def test_invisible_chars_at_boundaries(self):
        """Invisible characters at start/end should be removed."""
        text = "\u00AD\u200Bhello world\u200D\uFEFF"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_invisible_chars_with_normal_spaces(self):
        """Invisible chars should be removed alongside normal whitespace normalization."""
        text = "hello\u00AD \u200B  world\u200D"
        result = _sanitize_text(text)
        # Should normalize to single space and remove invisible chars
        assert result == "hello world"
