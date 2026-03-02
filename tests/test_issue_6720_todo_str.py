"""Tests for Todo.__str__ method (Issue #6720).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str output is distinct from repr (user-facing vs debug)
3. str output format is like '[x] #1: todo text'
4. Output is under 80 chars for normal todos
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_with_undone_todo() -> None:
    """str(Todo) should return user-friendly format for undone todo."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    # Should show unchecked status and todo text
    assert "[ ]" in result
    assert "#1" in result
    assert "buy milk" in result


def test_todo_str_with_done_todo() -> None:
    """str(Todo) should return user-friendly format for done todo."""
    todo = Todo(id=1, text="buy milk", done=True)
    result = str(todo)

    # Should show checked status and todo text
    assert "[x]" in result
    assert "#1" in result
    assert "buy milk" in result


def test_todo_str_format_matches_pattern() -> None:
    """str(Todo) should follow pattern '[x] #id: text' or '[ ] #id: text'."""
    todo_undone = Todo(id=42, text="task text", done=False)
    result_undone = str(todo_undone)

    # Format should be: [ ] #42: task text
    assert result_undone == "[ ] #42: task text"

    todo_done = Todo(id=42, text="task text", done=True)
    result_done = str(todo_done)

    # Format should be: [x] #42: task text
    assert result_done == "[x] #42: task text"


def test_todo_str_is_concise() -> None:
    """str(Todo) output should be concise (< 80 chars for normal todos)."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    assert len(result) < 80, f"str too long: {len(result)} chars - {result}"


def test_todo_str_distinct_from_repr() -> None:
    """str(Todo) should be distinct from repr(Todo)."""
    todo = Todo(id=1, text="buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be user-friendly, repr should be debug-friendly
    # repr contains class name, str does not
    assert "Todo" in repr_result
    assert "Todo" not in str_result

    # str uses [x]/[ ] notation, repr uses done=True/False
    assert "[ ]" in str_result or "[x]" in str_result
    assert "done=" in repr_result


def test_todo_str_with_various_ids() -> None:
    """str(Todo) should handle various id values."""
    # Single digit id
    todo1 = Todo(id=5, text="task", done=False)
    assert "#5" in str(todo1)

    # Large id
    todo2 = Todo(id=999, text="task", done=True)
    assert "#999" in str(todo2)


def test_todo_str_handles_special_characters() -> None:
    """str(Todo) should handle special characters in text."""
    # Text with quotes
    todo1 = Todo(id=1, text='text with "quotes"', done=False)
    result1 = str(todo1)
    assert "text with" in result1

    # Text with colon (should still work)
    todo2 = Todo(id=2, text="task: subtask", done=False)
    result2 = str(todo2)
    assert "task: subtask" in result2
