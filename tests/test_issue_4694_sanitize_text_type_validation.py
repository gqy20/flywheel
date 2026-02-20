"""Tests for _sanitize_text type validation (Issue #4694).

_sanitize_text should validate input types and raise TypeError
with a helpful message for non-string inputs, rather than
allowing an unhelpful AttributeError to occur.
"""

import pytest

from flywheel.formatter import _sanitize_text


class TestSanitizeTextTypeValidation:
    """Test that _sanitize_text validates input types."""

    def test_sanitize_text_none_raises_type_error(self) -> None:
        """_sanitize_text(None) should raise TypeError, not AttributeError."""
        with pytest.raises(TypeError, match=r"Expected str, got NoneType"):
            _sanitize_text(None)  # type: ignore[arg-type]

    def test_sanitize_text_int_raises_type_error(self) -> None:
        """_sanitize_text(123) should raise TypeError with helpful message."""
        with pytest.raises(TypeError, match=r"Expected str, got int"):
            _sanitize_text(123)  # type: ignore[arg-type]

    def test_sanitize_text_list_raises_type_error(self) -> None:
        """_sanitize_text(['a']) should raise TypeError with helpful message."""
        with pytest.raises(TypeError, match=r"Expected str, got list"):
            _sanitize_text(["a"])  # type: ignore[arg-type]

    def test_sanitize_text_dict_raises_type_error(self) -> None:
        """_sanitize_text({}) should raise TypeError with helpful message."""
        with pytest.raises(TypeError, match=r"Expected str, got dict"):
            _sanitize_text({})  # type: ignore[arg-type]

    def test_sanitize_text_valid_string_works(self) -> None:
        """Normal string input should still work correctly."""
        assert _sanitize_text("normal string") == "normal string"
        assert _sanitize_text("") == ""
        assert _sanitize_text("test\nnewline") == "test\\nnewline"
