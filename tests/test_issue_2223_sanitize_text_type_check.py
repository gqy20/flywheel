"""Regression tests for Issue #2223: _sanitize_text type checking.

This test file ensures that _sanitize_text raises TypeError for non-str inputs
instead of AttributeError.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


def test_sanitize_text_with_none_raises_typeerror() -> None:
    """_sanitize_text with None input should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="expected str"):
        _sanitize_text(None)


def test_sanitize_text_with_int_raises_typeerror() -> None:
    """_sanitize_text with int input should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="expected str"):
        _sanitize_text(123)


def test_sanitize_text_with_list_raises_typeerror() -> None:
    """_sanitize_text with list input should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="expected str"):
        _sanitize_text(["list", "of", "strings"])


def test_sanitize_text_with_dict_raises_typeerror() -> None:
    """_sanitize_text with dict input should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="expected str"):
        _sanitize_text({"key": "value"})


def test_sanitize_text_with_bytes_raises_typeerror() -> None:
    """_sanitize_text with bytes input should raise TypeError, not AttributeError."""
    with pytest.raises(TypeError, match="expected str"):
        _sanitize_text(b"bytes")


def test_sanitize_text_with_valid_string_works() -> None:
    """_sanitize_text with valid string should work normally."""
    result = _sanitize_text("Normal text")
    assert result == "Normal text"
