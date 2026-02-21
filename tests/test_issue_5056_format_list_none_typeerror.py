"""Regression tests for Issue #5056: format_list(None) should raise TypeError.

This test file ensures that passing None to format_list raises a clear TypeError
instead of silently returning "No todos yet.".
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter


def test_format_list_none_raises_type_error() -> None:
    """format_list(None) should raise TypeError, not return 'No todos yet.'."""
    with pytest.raises(TypeError, match="todos cannot be None"):
        TodoFormatter.format_list(None)  # type: ignore[arg-type]


def test_format_list_empty_still_works() -> None:
    """Empty list should still return 'No todos yet.'."""
    result = TodoFormatter.format_list([])
    assert result == "No todos yet."
