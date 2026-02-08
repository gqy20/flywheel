"""Regression tests for Issue #2223: _sanitize_text missing type checking.

The _sanitize_text function should raise a clear TypeError when passed
non-str types, rather than raising an AttributeError due to missing
.replace() method on non-string types.
"""

import pytest

from flywheel.formatter import _sanitize_text


class TestSanitizeTextTypeCheck:
    """Test that _sanitize_text validates input type."""

    def test_sanitize_text_raises_type_error_for_int(self):
        """_sanitize_text(123) should raise TypeError with clear message."""
        with pytest.raises(TypeError, match=r"Expected str, got int"):
            _sanitize_text(123)

    def test_sanitize_text_raises_type_error_for_none(self):
        """_sanitize_text(None) should raise TypeError with clear message."""
        with pytest.raises(TypeError, match=r"Expected str, got NoneType"):
            _sanitize_text(None)

    def test_sanitize_text_raises_type_error_for_list(self):
        """_sanitize_text([]) should raise TypeError with clear message."""
        with pytest.raises(TypeError, match=r"Expected str, got list"):
            _sanitize_text([])

    def test_sanitize_text_raises_type_error_for_dict(self):
        """_sanitize_text({}) should raise TypeError with clear message."""
        with pytest.raises(TypeError, match=r"Expected str, got dict"):
            _sanitize_text({})

    def test_sanitize_text_raises_type_error_for_float(self):
        """_sanitize_text(1.5) should raise TypeError with clear message."""
        with pytest.raises(TypeError, match=r"Expected str, got float"):
            _sanitize_text(1.5)

    def test_sanitize_works_with_normal_string(self):
        """Normal string input should work as expected."""
        result = _sanitize_text("normal text")
        assert result == "normal text"

    def test_sanitize_works_with_empty_string(self):
        """Empty string input should work as expected."""
        result = _sanitize_text("")
        assert result == ""

    def test_sanitize_works_with_control_chars(self):
        """String with control characters should still be sanitized properly."""
        result = _sanitize_text("text\nwith\nnewlines")
        assert result == r"text\nwith\nnewlines"

    def test_type_error_message_includes_actual_type(self):
        """TypeError message should include the actual type name for debugging."""
        with pytest.raises(TypeError) as exc_info:
            _sanitize_text(42)

        assert "Expected str" in str(exc_info.value)
        assert "got int" in str(exc_info.value)
