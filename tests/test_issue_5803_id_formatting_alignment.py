"""Regression tests for Issue #5803: ID formatting alignment for ID >= 1000.

This test file ensures that ID formatting maintains column alignment
even when IDs exceed 999 (i.e., 4+ digits).
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_list_column_alignment_with_large_ids() -> None:
    """List output should maintain consistent column alignment across varied ID sizes.

    This is the main regression test for issue #5803: when IDs >= 1000,
    the fixed 3-width format breaks column alignment in list output.
    """
    todos = [
        Todo(id=1, text="Task 1"),
        Todo(id=100, text="Task 100"),
        Todo(id=999, text="Task 999"),
        Todo(id=1000, text="Task 1000"),
        Todo(id=10000, text="Task 10000"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have the status marker at position 0-3: "[ ] "
    # and the task text should start after the ID
    for line in lines:
        assert line.startswith("[ ] "), f"Line should start with '[ ] ': {line!r}"

    # Verify specific line content - IDs should be right-aligned with consistent width
    # based on the maximum ID (10000 = 5 digits)
    assert lines[0] == "[ ]     1 Task 1"
    assert lines[1] == "[ ]   100 Task 100"
    assert lines[2] == "[ ]   999 Task 999"
    assert lines[3] == "[ ]  1000 Task 1000"
    assert lines[4] == "[ ] 10000 Task 10000"


def test_format_list_column_alignment_with_id_999_and_1000() -> None:
    """Test specific case where ID crosses the 1000 boundary."""
    todos = [
        Todo(id=999, text="Task 999"),
        Todo(id=1000, text="Task 1000"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Both lines should have the text starting at the same column
    # With max ID = 1000 (4 digits), alignment should use width 4
    assert lines[0] == "[ ]  999 Task 999"
    assert lines[1] == "[ ] 1000 Task 1000"


def test_format_list_single_large_id() -> None:
    """Single todo with large ID should still format correctly."""
    todos = [Todo(id=10000, text="Task 10000")]
    result = TodoFormatter.format_list(todos)
    # Should be properly formatted
    assert result == "[ ] 10000 Task 10000"


def test_format_list_zero_id_alignment() -> None:
    """ID=0 should be properly aligned in list output."""
    todos = [
        Todo(id=0, text="Task 0"),
        Todo(id=100, text="Task 100"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # With max ID = 100 (3 digits), ID=0 should be right-aligned to width 3
    assert lines[0] == "[ ]   0 Task 0"
    assert lines[1] == "[ ] 100 Task 100"


def test_format_list_negative_id_alignment() -> None:
    """Negative ID should still be readable and aligned (edge case)."""
    todos = [
        Todo(id=-1, text="Task negative"),
        Todo(id=100, text="Task 100"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Both lines should be readable
    assert "-1" in lines[0]
    assert "Task negative" in lines[0]
    assert "100" in lines[1]
    assert "Task 100" in lines[1]
