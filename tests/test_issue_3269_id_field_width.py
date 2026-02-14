"""Regression tests for Issue #3269: ID field width format misalignment for IDs >999.

This test file ensures that the ID field width properly aligns for IDs of
any size, using dynamic width based on the max ID in the list.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_with_id_9999() -> None:
    """ID 9999 should format correctly without overflow."""
    todo = Todo(id=9999, text="Test task")
    result = TodoFormatter.format_todo(todo)
    # Should contain the ID without truncation
    assert "9999" in result
    # Should be properly formatted with status bracket
    assert "[ ]" in result


def test_format_todo_with_id_100() -> None:
    """ID 100 should format correctly with right alignment."""
    todo = Todo(id=100, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert "[ ] 100 Test task" in result


def test_format_list_with_mixed_ids_under_1000() -> None:
    """format_list() with IDs [1, 100] should have aligned columns."""
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=100, text="Task hundred"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Both lines should have same structure: [ ] <ID> <text>
    # Extract the parts before the text
    line1_prefix = lines[0].split("Task")[0]
    line2_prefix = lines[1].split("Task")[0]

    # The prefixes should have the same length for proper alignment
    assert len(line1_prefix) == len(line2_prefix), (
        f"Misaligned prefixes: '{line1_prefix}' (len={len(line1_prefix)}) "
        f"vs '{line2_prefix}' (len={len(line2_prefix)})"
    )


def test_format_list_with_mixed_ids_over_1000() -> None:
    """format_list() with IDs [1, 100, 10000] should have aligned columns."""
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=100, text="Task hundred"),
        Todo(id=10000, text="Task ten thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have the same prefix length
    prefixes = [line.split("Task")[0] for line in lines]
    lengths = [len(p) for p in prefixes]

    assert len(set(lengths)) == 1, (
        f"Misaligned column widths: {list(zip(todos, prefixes, lengths))}"
    )


def test_format_list_with_large_ids() -> None:
    """format_list() should handle very large IDs correctly."""
    todos = [
        Todo(id=1, text="Small ID"),
        Todo(id=999, text="Three digit"),
        Todo(id=1000, text="Four digit"),
        Todo(id=9999, text="Max four digit"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have the same prefix length
    prefixes = []
    for line in lines:
        # Extract the part before the actual text content
        # Format is: [x] <ID> <text>
        parts = line.split(" ", 3)  # Split into: ['[x]', '<ID>', '<text>']
        if len(parts) >= 3:
            prefix = " ".join(parts[:2])  # '[x] <ID>'
            prefixes.append(prefix)

    lengths = [len(p) for p in prefixes]
    assert len(set(lengths)) == 1, (
        f"Misaligned columns for large IDs: {list(zip([t.id for t in todos], prefixes, lengths))}"
    )
