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
    # Should not have literal newlines in the repr output
    assert "\n" not in result2 or repr(result2).count("\\n") > 0


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


def test_todo_repr_escapes_ansi_escape_sequences() -> None:
    """repr(Todo) should escape ANSI escape sequences to prevent terminal injection.

    Regression test for Issue #2855.
    """
    # ANSI escape sequence for red text
    todo = Todo(id=1, text="\x1b[31mRED\x1b[0m")
    result = repr(todo)

    # Should contain escaped representation, not actual ESC character
    assert "\\x1b" in result, f"Expected escaped \\x1b in repr output: {result!r}"
    # Should not contain actual ESC character (0x1b)
    assert "\x1b" not in result, f"repr should not contain literal ESC character: {result!r}"


def test_todo_repr_escapes_control_characters() -> None:
    """repr(Todo) should escape C0/C1 control characters to prevent debugger manipulation.

    Regression test for Issue #2855.
    """
    # Test various control characters
    test_cases = [
        ("\x00", "\\x00"),  # Null byte
        ("\x07", "\\x07"),  # Bell
        ("\x7f", "\\x7f"),  # DEL
        ("\x80", "\\x80"),  # C1 control start
        ("\x9f", "\\x9f"),  # C1 control end
    ]

    for control_char, expected_escape in test_cases:
        todo = Todo(id=1, text=f"before{control_char}after")
        result = repr(todo)

        # Should contain escaped representation
        assert expected_escape in result, f"Expected {expected_escape} in repr for char {control_char!r}: {result!r}"
        # Should not contain actual control character
        assert control_char not in result, f"repr should not contain literal control character {control_char!r}: {result!r}"


def test_todo_repr_escapes_newline_carriage_return_tab() -> None:
    """repr(Todo) should escape \n, \r, \t to prevent multiline output in debugger.

    Regression test for Issue #2855.
    """
    # Newline injection attack
    todo1 = Todo(id=1, text="Buy milk\nFAKE_TODO")
    result1 = repr(todo1)
    # Should show escaped representation
    assert "\\n" in result1, f"Expected escaped \\n in repr: {result1!r}"
    # Should not have actual newline (prevents fake multiline output)
    assert "\n" not in result1, f"repr should not contain literal newline: {result1!r}"

    # Carriage return injection attack
    todo2 = Todo(id=2, text="Valid task\rFAKE_TASK")
    result2 = repr(todo2)
    assert "\\r" in result2, f"Expected escaped \\r in repr: {result2!r}"
    assert "\r" not in result2, f"repr should not contain literal carriage return: {result2!r}"

    # Tab injection
    todo3 = Todo(id=3, text="Task\twith\ttabs")
    result3 = repr(todo3)
    assert "\\t" in result3, f"Expected escaped \\t in repr: {result3!r}"
    assert "\t" not in result3, f"repr should not contain literal tab: {result3!r}"


def test_todo_repr_normal_text_unchanged() -> None:
    """repr(Todo) should not alter normal text without control characters.

    Regression test for Issue #2855.
    """
    todo = Todo(id=1, text="Buy milk and eggs")
    result = repr(todo)

    # Normal text should be preserved
    assert "Buy milk and eggs" in result
