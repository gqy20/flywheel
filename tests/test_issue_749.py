"""Test for Issue #749 - Verify sanitize_tags function implementation.

Issue #749 claims that sanitize_tags function logic is incomplete.
This test verifies that the sanitization logic is actually implemented correctly.
"""

from flywheel.cli import sanitize_tags


def test_sanitize_tags_filters_special_characters():
    """Test that sanitize_tags properly filters special characters.

    This is the main test for Issue #749 which claims the filtering logic
    is not implemented. This test proves it IS implemented.
    """
    # Test with various special characters that should be filtered out
    result = sanitize_tags("valid-tag, invalid@tag, test#tag, admin$drop")
    assert result == ["valid-tag", "invalidtag", "testtag", "admindrop"], (
        f"Expected special characters to be filtered, got {result}"
    )


def test_sanitize_tags_preserves_allowed_chars():
    """Test that allowed characters (alphanumeric, underscore, hyphen) are preserved."""
    result = sanitize_tags("abc123, test_tag, test-tag, Test_123-Tag")
    assert result == ["abc123", "test_tag", "test-tag", "Test_123-Tag"], (
        f"Expected allowed characters to be preserved, got {result}"
    )


def test_sanitize_tags_empty_after_sanitization():
    """Test that tags that become empty after sanitization are not included."""
    result = sanitize_tags("@@@, ###, $$$")
    assert result == [], (
        f"Expected empty list when all tags are invalid, got {result}"
    )


def test_sanitize_tags_filters_unicode_spoofing():
    """Test that Unicode spoofing characters are filtered out."""
    # Fullwidth characters (should be filtered)
    result = sanitize_tags("ｆｕｌｌｗｉｄｔｈ")
    assert result == [], (
        f"Expected fullwidth characters to be filtered, got {result}"
    )

    # Zero-width characters (should be filtered)
    result = sanitize_tags("test\u200Btag")  # Contains zero-width space
    assert result == ["testtag"], (
        f"Expected zero-width characters to be filtered, got {result}"
    )


def test_sanitize_tags_filters_control_characters():
    """Test that control characters are filtered out."""
    # Newlines, null bytes, etc. should be filtered
    result = sanitize_tags("test\ntag, test\x00tag")
    assert result == ["testtag", "testtag"], (
        f"Expected control characters to be filtered, got {result}"
    )


def test_sanitize_tags_handles_sql_injection_attempts():
    """Test that SQL injection attempts are neutralized."""
    result = sanitize_tags("'; DROP TABLE todos; --', admin' OR '1'='1")
    # Special characters should be filtered, leaving only alphanumeric
    assert result == ["DROPTABLEtodos", "adminOR11"], (
        f"Expected SQL injection attempts to be neutralized, got {result}"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
