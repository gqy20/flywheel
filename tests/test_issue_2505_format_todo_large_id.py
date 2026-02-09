"""Regression tests for Issue #2505: format_todo with 4+ digit IDs.

This test file ensures that format_todo properly handles IDs >= 1000,
which currently misalign due to fixed width of 3 in the format string.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_with_small_id() -> None:
    """Small ID (single digit) should format with 4-width padding."""
    todo = Todo(id=1, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # After fix: width 4 with right alignment
    assert result == "[ ]    1 Buy milk"


def test_format_todo_with_two_digit_id() -> None:
    """Two-digit ID should format with 4-width padding."""
    todo = Todo(id=42, text="Answer question")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   42 Answer question"


def test_format_todo_with_three_digit_id() -> None:
    """Three-digit ID should format with 4-width padding."""
    todo = Todo(id=999, text="Boundary test")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]  999 Boundary test"


def test_format_todo_with_id_1000() -> None:
    """Four-digit ID (1000) should format correctly without misalignment.

    The issue is that with width 3, 1000 just gets printed as "1000" but
    doesn't align properly with smaller IDs. After increasing width to 4,
    it should align correctly.
    """
    todo = Todo(id=1000, text="Test")
    result = TodoFormatter.format_todo(todo)
    # The ID should be "1000" - Python doesn't truncate, just no padding
    assert "1000" in result
    assert result == "[ ] 1000 Test"


def test_format_todo_with_id_9999() -> None:
    """Four-digit ID (9999) should format correctly at max 4-digit width."""
    todo = Todo(id=9999, text="Max ID test")
    result = TodoFormatter.format_todo(todo)
    # The ID should be "9999"
    assert "9999" in result
    assert result == "[ ] 9999 Max ID test"


def test_format_list_with_large_ids() -> None:
    """List with mixed ID sizes should align properly."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=999, text="Three digits"),
        Todo(id=1000, text="Four digits"),
        Todo(id=9999, text="Max 4-digit"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 4
    assert "[ ]    1 Small ID" in lines[0]
    assert "[ ]  999 Three digits" in lines[1]
    assert "[ ] 1000 Four digits" in lines[2]
    assert "[ ] 9999 Max 4-digit" in lines[3]
