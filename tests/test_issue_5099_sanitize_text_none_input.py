"""Regression tests for Issue #5099: _sanitize_text does not handle None input.

This test file ensures that _sanitize_text raises a clear TypeError
when passed None instead of silently failing with AttributeError.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import _sanitize_text


def test_sanitize_text_none_raises_typeerror() -> None:
    """_sanitize_text(None) should raise TypeError with clear message."""
    with pytest.raises(TypeError) as exc_info:
        _sanitize_text(None)  # type: ignore[arg-type]
    assert "text must be a string, not NoneType" in str(exc_info.value)
