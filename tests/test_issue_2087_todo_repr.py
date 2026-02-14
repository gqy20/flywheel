"""Tests for Todo.__repr__ method (Issue #2087).

These tests verify that:
1. Todo objects have a useful __repr__ for debugging
2. repr output is concise (< 80 chars for normal todos)
3. Long text is truncated in repr
4. repr handles special characters properly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_with_all_fields() -> None:
    """repr(Todo) should return readable format with all key fields."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = repr(todo)

    # Should include class name and key fields
    assert "Todo" in result
    assert "id=1" in result
    assert "text=" in result
    assert "done=False" in result

    # Text should be quoted
    assert "'buy milk'" in result or '"buy milk"' in result


def test_todo_repr_with_minimal_fields() -> None:
    """repr(Todo) should work with minimal required fields."""
    todo = Todo(id=42, text="minimal")
    result = repr(todo)

    assert "Todo" in result
    assert "id=42" in result
    assert "text=" in result
    assert "done=False" in result


def test_todo_repr_with_done_true() -> None:
    """repr(Todo) should show done=True for completed todos."""
    todo = Todo(id=1, text="completed task", done=True)
    result = repr(todo)

    assert "done=True" in result


def test_todo_repr_is_concise() -> None:
    """repr(Todo) output should be concise (< 80 chars for normal todos)."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = repr(todo)

    assert len(result) < 80, f"repr too long: {len(result)} chars - {result}"


def test_todo_repr_truncates_long_text() -> None:
    """repr(Todo) should truncate long text (> 50 chars)."""
    long_text = "a" * 100
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Truncated representation should not be excessively long
    assert len(result) < 150, f"repr should truncate long text: {len(result)} chars"
    # Should contain ellipsis or similar truncation indicator
    assert "..." in result or len(result) < 100


def test_todo_repr_handles_special_characters() -> None:
    """repr(Todo) should handle special characters (quotes, newlines, etc.)."""
    # Text with quotes
    todo1 = Todo(id=1, text='text with "quotes"')
    result1 = repr(todo1)
    assert "Todo" in result1

    # Text with newlines - repr should escape or handle them
    todo2 = Todo(id=2, text="line1\nline2")
    result2 = repr(todo2)
    assert "Todo" in result2
    # Should not have literal newlines in the repr output (issue #3255)
    assert "\n" not in result2, f"repr should not contain literal newline: {result2!r}"


def test_todo_repr_eval_able_optional() -> None:
    """repr(Todo) output should ideally be eval-able or at least informative."""
    todo = Todo(id=1, text="simple task", done=True)
    result = repr(todo)

    # At minimum, should contain all key information to recreate the object
    assert "id=1" in result
    assert "simple task" in result
    assert "done=True" in result


def test_todo_repr_multiple_todos_distinct() -> None:
    """repr(Todo) should make different todos distinguishable in debugger."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)

    repr1 = repr(todo1)
    repr2 = repr(todo2)

    # Different todos should have different reprs
    assert repr1 != repr2
    # Key distinguishing info should be present
    assert "id=1" in repr1
    assert "id=2" in repr2


def test_todo_repr_escapes_ansi_sequences() -> None:
    """repr(Todo) should escape ANSI escape sequences to prevent terminal manipulation.

    Regression test for issue #3255.
    """
    # Text with ANSI escape sequence (red color)
    todo = Todo(id=1, text="a\x1b[31mRed\x1b[0mb")
    result = repr(todo)

    # Should NOT contain the raw ESC character (0x1b)
    assert "\x1b" not in result, f"repr should not contain raw ESC character: {result!r}"
    # Should contain escaped version like \\x1b
    assert "\\x1b" in result, f"repr should contain escaped ESC sequence: {result!r}"


def test_todo_repr_escapes_newlines() -> None:
    """repr(Todo) should escape newlines to ensure single-line output.

    Regression test for issue #3255.
    """
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should NOT contain literal newline in the repr output itself
    assert "\n" not in result, f"repr should not contain literal newline: {result!r}"
    # Should contain escaped version like \\n
    assert "\\n" in result, f"repr should contain escaped newline: {result!r}"


def test_todo_repr_escapes_other_control_chars() -> None:
    """repr(Todo) should escape other control characters like TAB, DEL, etc.

    Regression test for issue #3255.
    """
    # Text with TAB character
    todo = Todo(id=1, text="col1\tcol2")
    result = repr(todo)
    assert "\t" not in result, f"repr should not contain literal TAB: {result!r}"
    assert "\\t" in result, f"repr should contain escaped TAB: {result!r}"

    # Text with C1 control character
    todo2 = Todo(id=2, text="text\x80more")
    result2 = repr(todo2)
    assert "\x80" not in result2, f"repr should not contain raw C1 control: {result2!r}"
