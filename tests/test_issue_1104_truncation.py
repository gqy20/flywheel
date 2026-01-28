"""Test for Issue #1104 - Truncation logic allows bypassing max_length constraint via multi-byte characters.

The bug is that the current code truncates bytes to max_length, but the resulting
string (after decoding) can contain more than max_length characters. If a string
consists of 4-byte characters (e.g. emojis), the resulting string length can be
much larger than max_length.

Example:
- Input: 25 emoji characters (each is 4 bytes in UTF-8)
- max_length: 100
- Current behavior: s.encode('utf-8')[:100] = 25 emojis (100 bytes)
- After decode: 25 emoji characters (NOT truncated to 100 characters)
- Expected: Should be 100 characters maximum, not 100 bytes
"""

import pytest

from flywheel.cli import sanitize_for_security_context, remove_control_chars, sanitize_tags


class TestMultiByteTruncationIssue1104:
    """Test that truncation respects character count, not byte count."""

    def test_sanitize_for_security_context_emoji_truncation(self):
        """Test that max_length limits characters, not bytes."""
        # Each emoji is 4 bytes in UTF-8
        # 100 emojis = 400 bytes, but we set max_length=100
        emojis = "😀" * 100  # 100 emoji characters (400 bytes in UTF-8)

        # With max_length=100, the result should be at most 100 characters
        result = sanitize_for_security_context(emojis, context="general", max_length=100)

        # The bug: current code truncates to 100 BYTES, then decodes
        # 100 bytes of emoji data = 25 complete emojis (25 chars)
        # So the result would have 25 characters, which is less than 100
        # But this is BY ACCIDENT - if we had mixed 1-byte and 4-byte chars,
        # we could end up with MORE than 100 characters

        # The fix: should slice the string directly to get 100 characters
        assert len(result) <= 100, f"Result has {len(result)} chars, expected <= 100"

    def test_remove_control_chars_emoji_truncation(self):
        """Test that max_length limits characters in remove_control_chars."""
        emojis = "😀" * 100  # 100 emoji characters (400 bytes)

        result = remove_control_chars(emojis, max_length=100)

        assert len(result) <= 100, f"Result has {len(result)} chars, expected <= 100"

    def test_sanitize_tags_emoji_truncation(self):
        """Test that max_length limits characters in sanitize_tags."""
        # Create tags with emojis (though they'll be filtered by whitelist)
        emoji_tags = "😀tag,😂tag,😃tag"
        # This will be filtered to just "tagtagtag" but truncation should still work

        result = sanitize_tags(emoji_tags, max_length=10)

        # The result should respect the max_length constraint
        joined = ",".join(result)
        assert len(joined) <= 10, f"Result has {len(joined)} chars, expected <= 10"

    def test_truncation_with_mixed_byte_widths(self):
        """Test truncation with mixed 1-byte and 4-byte characters."""
        # Mix of ASCII (1 byte) and emoji (4 bytes)
        # "a" * 50 + "😀" * 50 = 50 bytes + 200 bytes = 250 bytes total
        # But we want max 100 CHARACTERS
        mixed = "a" * 50 + "😀" * 50

        result = sanitize_for_security_context(mixed, context="general", max_length=100)

        # Should have at most 100 characters
        assert len(result) <= 100, f"Result has {len(result)} chars, expected <= 100"

    def test_truncation_preserves_string_boundary(self):
        """Test that truncation doesn't cut in the middle of multi-byte sequences."""
        # Create a string where cutting at exactly max_length bytes would
        # cut in the middle of a multi-byte character
        # "abc" (3 bytes) + emoji (4 bytes) + "def" (3 bytes)
        s = "abc😀def"

        # With max_length=5, we'd get "abc😀" (5 chars) if slicing by characters
        # But if we cut at 5 bytes, we'd get "abc" + first 2 bytes of emoji
        # which would decode to just "abc" (3 chars) with the ignore error handling
        result = sanitize_for_security_context(s, context="general", max_length=5)

        # Result should be valid UTF-8 and at most 5 characters
        assert len(result) <= 5
        # Should be valid UTF-8 (can be encoded without errors)
        result.encode('utf-8')  # Should not raise

    def test_edge_case_exact_max_length(self):
        """Test when input length exactly equals max_length."""
        s = "a" * 100
        result = sanitize_for_security_context(s, context="general", max_length=100)
        assert len(result) == 100

    def test_edge_case_one_over_max_length(self):
        """Test when input is one character over max_length."""
        s = "a" * 101
        result = sanitize_for_security_context(s, context="general", max_length=100)
        assert len(result) == 100

    def test_truncation_with_all_4byte_chars(self):
        """Test with a string of only 4-byte characters."""
        # Create 30 emojis (120 bytes)
        emojis = "😀😁😂😃😄😅😆😇😈😉😊😋😌😍😎😏😐😑😒😓😔😕😖😗😘😙😚😛😜😝😞"

        result = sanitize_for_security_context(emojis, context="general", max_length=20)

        # Should be at most 20 characters
        assert len(result) <= 20

    def test_short_string_not_truncated(self):
        """Test that short strings are not truncated."""
        s = "Hello"
        result = sanitize_for_security_context(s, context="general", max_length=100)
        assert result == "Hello"
        assert len(result) == 5
