"""Regression tests for Issue #4694: _sanitize_text type validation.

This test file ensures that _sanitize_text raises a helpful TypeError
when called with non-string input instead of an unhelpful AttributeError.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


class TestSanitizeTextTypeValidation:
    """Test that _sanitize_text validates input type properly."""

    def test_none_input_raises_type_error(self) -> None:
        """_sanitize_text(None) should raise TypeError, not AttributeError."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text(None)
        assert "Expected str, got NoneType" in str(exc_info.value)

    def test_int_input_raises_type_error(self) -> None:
        """_sanitize_text(123) should raise TypeError with helpful message."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text(123)
        assert "Expected str, got int" in str(exc_info.value)

    def test_list_input_raises_type_error(self) -> None:
        """_sanitize_text(['a']) should raise TypeError with helpful message."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text(["a"])
        assert "Expected str, got list" in str(exc_info.value)

    def test_dict_input_raises_type_error(self) -> None:
        """_sanitize_text({}) should raise TypeError with helpful message."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text({})
        assert "Expected str, got dict" in str(exc_info.value)

    def test_bytes_input_raises_type_error(self) -> None:
        """_sanitize_text(b'data') should raise TypeError with helpful message."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text(b"data")
        assert "Expected str, got bytes" in str(exc_info.value)


class TestSanitizeTextNormalBehavior:
    """Regression tests to ensure normal string behavior is unchanged."""

    def test_normal_string_unchanged(self) -> None:
        """Normal string without special characters should pass through."""
        result = _sanitize_text("Hello, World!")
        assert result == "Hello, World!"

    def test_empty_string_unchanged(self) -> None:
        """Empty string should remain empty."""
        assert _sanitize_text("") == ""

    def test_backslash_escaping_still_works(self) -> None:
        """Backslash escaping should still work after adding type check."""
        result = _sanitize_text("C:\\path\\to\\file")
        assert result == r"C:\\path\\to\\file"

    def test_control_char_escaping_still_works(self) -> None:
        """Control character escaping should still work after adding type check."""
        result = _sanitize_text("Line1\nLine2")
        assert result == r"Line1\nLine2"
