"""Regression tests for Issue #4694: _sanitize_text type validation.

This test file ensures that _sanitize_text raises TypeError with a helpful
message for non-string input, rather than an unhelpful AttributeError.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


def test_sanitize_text_raises_type_error_for_none() -> None:
    """_sanitize_text(None) should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError) as exc_info:
        _sanitize_text(None)  # type: ignore[arg-type]
    assert "Expected str, got NoneType" in str(exc_info.value)


def test_sanitize_text_raises_type_error_for_int() -> None:
    """_sanitize_text(int) should raise TypeError with helpful message."""
    with pytest.raises(TypeError) as exc_info:
        _sanitize_text(123)  # type: ignore[arg-type]
    assert "Expected str, got int" in str(exc_info.value)


def test_sanitize_text_raises_type_error_for_list() -> None:
    """_sanitize_text(list) should raise TypeError with helpful message."""
    with pytest.raises(TypeError) as exc_info:
        _sanitize_text(["a", "b"])  # type: ignore[arg-type]
    assert "Expected str, got list" in str(exc_info.value)


def test_sanitize_text_normal_string_unchanged() -> None:
    """Normal string input should return correct sanitized output."""
    result = _sanitize_text("normal string")
    assert result == "normal string"


def test_sanitize_text_escapes_backslash() -> None:
    """Backslash should be properly escaped."""
    result = _sanitize_text("path\\to\\file")
    assert result == "path\\\\to\\\\file"
