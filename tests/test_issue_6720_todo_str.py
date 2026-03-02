"""Tests for Todo.__str__ method (Issue #6720).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str output is distinct from repr (user vs debug format)
3. str output follows format: [x] #<id>: <text>
4. Output is under 80 chars for normal todos
5. Control characters are sanitized properly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_with_undone_todo() -> None:
    """str(Todo) should return user-friendly format for undone todo."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    # Should match format: [ ] #1: buy milk
    assert result == "[ ] #1: buy milk"


def test_todo_str_with_done_todo() -> None:
    """str(Todo) should return user-friendly format for done todo."""
    todo = Todo(id=1, text="buy milk", done=True)
    result = str(todo)

    # Should match format: [x] #1: buy milk
    assert result == "[x] #1: buy milk"


def test_todo_str_distinct_from_repr() -> None:
    """str(Todo) should be distinct from repr(Todo) - user vs debug format."""
    todo = Todo(id=1, text="buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be user-friendly format
    assert str_result == "[ ] #1: buy milk"
    # repr should be debug format
    assert "Todo(" in repr_result
    # They should be different
    assert str_result != repr_result


def test_todo_str_is_concise() -> None:
    """str(Todo) output should be concise (< 80 chars for normal todos)."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    assert len(result) < 80, f"str too long: {len(result)} chars - {result}"


def test_todo_str_with_larger_id() -> None:
    """str(Todo) should format larger IDs correctly."""
    todo = Todo(id=42, text="task with larger id", done=True)
    result = str(todo)

    assert result == "[x] #42: task with larger id"


def test_todo_str_with_special_characters() -> None:
    """str(Todo) should sanitize control characters in text."""
    # Text with newline should be sanitized
    todo = Todo(id=1, text="line1\nline2", done=False)
    result = str(todo)

    # Should not contain literal newline
    assert "\n" not in result
    # Should contain escaped newline
    assert "\\n" in result


def test_todo_str_with_tab_character() -> None:
    """str(Todo) should sanitize tab characters in text."""
    todo = Todo(id=1, text="col1\tcol2", done=False)
    result = str(todo)

    # Should not contain literal tab
    assert "\t" not in result
    # Should contain escaped tab
    assert "\\t" in result


def test_todo_str_with_backslash() -> None:
    """str(Todo) should escape backslashes properly."""
    todo = Todo(id=1, text="path\\to\\file", done=False)
    result = str(todo)

    # Backslash should be escaped
    assert "\\\\" in result


def test_todo_str_multiple_todos_distinct() -> None:
    """str(Todo) should make different todos distinguishable."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)

    str1 = str(todo1)
    str2 = str(todo2)

    # Different todos should have different str
    assert str1 != str2
    assert "[ ]" in str1  # undone
    assert "[x]" in str2  # done
