"""Regression tests for Issue #2388: format_todo uses fixed width formatting (>3) for todo.id, causing column misalignment.

This test file ensures that todo IDs with 4+ digits are properly aligned in the output.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_with_4_digit_id() -> None:
    """Todo with ID >= 1000 should be displayed without overflow.

    The current implementation uses >3 format specifier which only allocates
    3 characters for the ID, causing IDs >= 1000 (4+ digits) to overflow
    and break column alignment.
    """
    todo = Todo(id=1000, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Current broken format: "[ ] 1000 Buy milk" (no space after 1000)
    # Expected fixed format: "[ ] 1000 Buy milk" (with proper spacing)
    assert "[ ]" in result
    assert "1000" in result
    assert "Buy milk" in result


def test_format_list_maintains_alignment() -> None:
    """Multiple todos with varying ID widths should maintain column alignment.

    When displaying a list of todos with IDs of varying widths (1, 99, 999, 1000, 99999),
    the task text should start at a consistent column position regardless of ID width.

    This test verifies the current buggy behavior where IDs >= 1000 cause misalignment.
    """
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=99, text="Task two"),
        Todo(id=999, text="Task three"),
        Todo(id=1000, text="Task four"),
        Todo(id=99999, text="Task five"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 5

    # Find the column position where the task text starts for each line
    # With fixed width >3, lines 1-3 have text at same position, but line 4+ shift
    text_positions = [line.index(task.text.split()[0]) for line, task in zip(lines, todos, strict=True)]

    # Current buggy behavior: positions 0,1,2 are the same, but position 3,4 differ
    # This test documents the bug - the first 3 IDs (<=999) align but 1000+ doesn't
    assert text_positions[0] == text_positions[1] == text_positions[2], \
        "IDs < 1000 should align (currently true)"

    # This assertion will FAIL with current implementation (format uses >3)
    # because ID 1000 is 4 digits and overflows the 3-character width
    assert text_positions[2] == text_positions[3] == text_positions[4], \
        "All task text should start at the same column (BUG: currently fails for IDs >= 1000)"


def test_format_todo_with_5_digit_id() -> None:
    """Todo with ID >= 10000 should be displayed correctly."""
    todo = Todo(id=99999, text="Big ID task")
    result = TodoFormatter.format_todo(todo)
    assert "[ ]" in result
    assert "99999" in result
    assert "Big ID task" in result
