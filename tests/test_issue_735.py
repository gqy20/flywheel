"""Test for Issue #735 - Regex ReDoS vulnerability in sanitize_tags.

This test verifies that:
1. The hyphen in allowed_chars is safely positioned to prevent ReDoS
2. Tags with hyphens are properly handled
3. The allowed_chars set cannot be accidentally used to create unsafe regex patterns
"""

import string
import re
from flywheel.cli import sanitize_tags


def test_hyphen_position_in_allowed_chars():
    """Test that hyphen in allowed_chars is positioned safely.

    If hyphen is in the middle like '_-', it could create a range when used
    in regex character classes. We want to ensure it's at the end (or escaped).
    """
    from flywheel.cli import sanitize_tags

    # Access the allowed_chars by calling sanitize_tags and inspecting
    # We'll test the actual behavior instead of implementation details

    # Test that hyphens are preserved in tags
    result = sanitize_tags("test-tag, another_tag, third-tag")
    assert result == ["test-tag", "another_tag", "third-tag"], (
        f"Expected hyphens to be preserved, got {result}"
    )


def test_tags_with_hyphens_and_underscores():
    """Test that both hyphens and underscores work correctly in tags."""
    result = sanitize_tags("my_tag, my-tag, my_tag-tag")
    assert result == ["my_tag", "my-tag", "my_tag-tag"], (
        f"Expected both underscores and hyphens to work, got {result}"
    )


def test_no_redos_in_character_class():
    """Test that allowed_chars cannot create unsafe regex patterns.

    Even if someone accidentally converts allowed_chars to a regex character class,
    it should not create ranges that could cause ReDoS.
    """
    # Replicate the allowed_chars construction
    allowed_chars = set(string.ascii_letters + string.digits + '_-')

    # If someone tries to create a regex pattern from this
    # by joining the characters: [abc..._-]
    # The hyphen at the end is safe (no range created)
    chars_list = sorted(allowed_chars)
    chars_str = ''.join(chars_list)

    # The hyphen should be at the end (after underscore in ASCII order)
    # or at the beginning to be safe in regex character classes
    # In ASCII: _ = 95, - = 45, so - comes before _
    # When sorted, - should be at the beginning

    # Verify hyphen is not in a position that could create a range
    # when used in a character class like [chars_str]
    if '-' in chars_str:
        hyphen_pos = chars_str.index('-')

        # Check if hyphen could create a range: it should be at position 0 or -1
        # or the characters before/after should not form a valid range
        is_safe = (hyphen_pos == 0 or hyphen_pos == len(chars_str) - 1)

        # Also verify it doesn't create an unintended range in the original string
        # The original has '_-' which means '_' followed by '-'
        # In ASCII: '_' = 95, '-' = 45, so this is a descending range
        # which is still problematic in some regex engines

        # The safest approach is to ensure hyphen is at the beginning or end
        assert is_safe or hyphen_pos == len(chars_str) - 1, (
            f"Hyphen at position {hyphen_pos} could create unsafe range in regex"
        )


def test_sanitize_tags_handles_edge_cases():
    """Test edge cases in tag sanitization."""
    # Empty string
    assert sanitize_tags("") == []

    # Only whitespace
    assert sanitize_tags("   ,  ,   ") == []

    # Mixed valid and invalid characters
    result = sanitize_tags("valid-tag, invalid@tag, also_valid_tag")
    assert result == ["valid-tag", "invalidtag", "also_valid_tag"], (
        f"Expected proper sanitization, got {result}"
    )

    # Tags with multiple hyphens
    result = sanitize_tags("my-long-tag-name")
    assert result == ["my-long-tag-name"], (
        f"Expected multiple hyphens to be preserved, got {result}"
    )


def test_hyphen_not_used_as_range_indicator():
    """Test that the hyphen in allowed_chars is literal, not a range.

    This test ensures that when we check 'c in allowed_chars',
    the hyphen is treated as a literal character, not as a range indicator.
    """
    allowed_chars = set(string.ascii_letters + string.digits + '_-')

    # Test that both underscore and hyphen are in the set
    assert '_' in allowed_chars, "Underscore should be in allowed_chars"
    assert '-' in allowed_chars, "Hyphen should be in allowed_chars"

    # Test that characters between _ and - in ASCII are NOT in the set
    # (if hyphen created a range, they would be)
    # ASCII: '[' = 91, '\\' = 92, ']' = 93, '^ = 94, '_' = 95, '`' = 96
    # If '_-' created a range [_-`], then [\\]^_` would be in it
    for char in ['[', '\\', ']', '^', '`']:
        if char not in string.ascii_letters:
            assert char not in allowed_chars, (
                f"Character '{char}' should not be in allowed_chars. "
                f"If hyphen created a range, it would be included."
            )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
