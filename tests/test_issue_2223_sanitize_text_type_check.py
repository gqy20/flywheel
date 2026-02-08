"""Regression tests for Issue #2223: _sanitize_text type checking.

This test file ensures that _sanitize_text properly validates input types
and raises TypeError (not AttributeError) for non-string inputs.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


def test_sanitize_text_with_int_raises_typeerror() -> None:
    """Passing int should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="Expected str, got int"):
        _sanitize_text(123)


def test_sanitize_text_with_none_raises_typeerror() -> None:
    """Passing None should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="Expected str, got NoneType"):
        _sanitize_text(None)


def test_sanitize_text_with_list_raises_typeerror() -> None:
    """Passing list should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="Expected str, got list"):
        _sanitize_text(["test"])


def test_sanitize_text_with_normal_string_works() -> None:
    """Normal string input should work correctly."""
    result = _sanitize_text("normal text")
    assert result == "normal text"


def test_sanitize_text_with_special_chars_works() -> None:
    """String with special characters should still be sanitized correctly."""
    result = _sanitize_text("text\nwith\tnewline")
    assert result == "text\\nwith\\tnewline"
