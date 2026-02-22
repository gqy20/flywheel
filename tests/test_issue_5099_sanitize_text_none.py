"""Regression tests for Issue #5099: _sanitize_text does not handle None input.

This test file ensures that _sanitize_text properly handles None input
by raising TypeError with a clear message.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


def test_sanitize_text_none_raises_type_error() -> None:
    """_sanitize_text(None) should raise TypeError with clear message."""
    with pytest.raises(TypeError) as exc_info:
        _sanitize_text(None)  # type: ignore[arg-type]
    assert "text must be a string, not NoneType" in str(exc_info.value)


def test_sanitize_text_empty_string() -> None:
    """_sanitize_text('') should return empty string."""
    result = _sanitize_text("")
    assert result == ""


def test_sanitize_text_normal_string() -> None:
    """_sanitize_text with normal string should work as before."""
    result = _sanitize_text("Hello World")
    assert result == "Hello World"
