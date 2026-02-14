"""Regression tests for Issue #3269: ID field width format alignment.

This test file ensures that ID field width formatting properly aligns
for IDs > 999, preventing table formatting issues.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_1_alignment() -> None:
    """ID 1 should be right-aligned in 4-char field."""
    todo = Todo(id=1, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should be "[ ]    1 Task" with 3 spaces before the 1
    assert result == "[ ]    1 Task"


def test_format_todo_id_99_alignment() -> None:
    """ID 99 should be right-aligned in 4-char field."""
    todo = Todo(id=99, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should be "[ ]   99 Task" with 2 spaces before 99
    assert result == "[ ]   99 Task"


def test_format_todo_id_999_alignment() -> None:
    """ID 999 should be right-aligned in 4-char field."""
    todo = Todo(id=999, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should be "[ ]  999 Task" with 1 space before 999
    assert result == "[ ]  999 Task"


def test_format_todo_id_1000_alignment() -> None:
    """ID 1000 should fit in 4-char field without overflow."""
    todo = Todo(id=1000, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should be "[ ] 1000 Task" with no space before 1000
    assert result == "[ ] 1000 Task"


def test_format_todo_id_9999_alignment() -> None:
    """ID 9999 should fit in 4-char field without overflow."""
    todo = Todo(id=9999, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should be "[ ] 9999 Task" with no space before 9999
    assert result == "[ ] 9999 Task"


def test_format_list_mixed_ids_column_alignment() -> None:
    """format_list() with mixed ID sizes should maintain column alignment."""
    todos = [
        Todo(id=1, text="First"),
        Todo(id=100, text="Second"),
        Todo(id=9999, text="Third"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Verify the "Task" column starts at the same position for all lines
    # The format is "[ ] {id:>4} {text}" so text should start at position 9
    # (4 for "[ ] " + 4 for ID + 1 for space = 9)
    expected_lines = [
        "[ ]    1 First",
        "[ ]  100 Second",
        "[ ] 9999 Third",
    ]
    assert lines == expected_lines

    # Verify all lines have the same column alignment for the text
    for i, line in enumerate(lines):
        # Find the position where the text starts (after ID field)
        # Format: "[ ] {id:>4} {text}"
        # "[ ] " is 4 chars, ID field is 4 chars, " " is 1 char = 9 chars total before text
        text_start = line.find(todos[i].text)
        assert text_start == 9, f"Text for todo {todos[i].id} starts at wrong position: {text_start}"


def test_format_todo_done_status_preserved() -> None:
    """Done status should still work correctly with new field width."""
    todo = Todo(id=123, text="Done task", done=True)
    result = TodoFormatter.format_todo(todo)
    # Should be "[x]  123 Done task"
    assert result == "[x]  123 Done task"
