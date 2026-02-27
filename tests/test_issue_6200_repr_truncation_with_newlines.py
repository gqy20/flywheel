"""Tests for Todo.__repr__ truncation with newlines (Issue #6200).

These tests verify that:
1. repr output length is bounded and predictable even when text contains newlines
2. Truncation indicator '...' appears when original text exceeds limit
3. repr never exceeds 120 chars total for any input
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_with_leading_newlines_is_bounded() -> None:
    """repr(Todo) with text starting with many newlines should stay bounded.

    This is the key edge case: when the truncated portion is all newlines,
    each newline becomes 2 chars (\\n) in the escaped repr, causing the
    output to be much longer than expected.
    """
    # 50 newlines followed by 50 'a' chars = 100 chars total
    # Truncation takes first 47 chars = 47 newlines
    # Each escaped newline is 2 chars, so escaped text = 94 chars
    # This should cause repr to exceed 120 chars if not handled properly
    text = "\n" * 50 + "a" * 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # repr output should never exceed 120 chars total
    assert len(result) < 120, f"repr too long: {len(result)} chars - {result}"


def test_todo_repr_with_many_newlines_shows_truncation() -> None:
    """repr(Todo) with long text containing newlines should show truncation indicator."""
    # Create text with 121 chars (60 newlines + 60 'a' chars)
    text = "a\n" * 60  # 121 chars total
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should contain truncation indicator
    assert "..." in result, f"Expected truncation indicator in: {result}"


def test_todo_repr_with_tabs_is_bounded() -> None:
    """repr(Todo) with text containing many tabs should stay bounded."""
    # Similar to newlines, tabs also get escaped
    text = "\t" * 50 + "a" * 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # repr output should never exceed 120 chars total
    assert len(result) < 120, f"repr too long: {len(result)} chars - {result}"


def test_todo_repr_normal_text_still_works() -> None:
    """repr(Todo) truncation fix should not break normal text handling."""
    # Short text should not be truncated
    todo = Todo(id=1, text="simple task")
    result = repr(todo)
    assert "simple task" in result
    assert "..." not in result

    # Long text without special chars should still truncate
    long_text = "a" * 100
    todo2 = Todo(id=2, text=long_text)
    result2 = repr(todo2)
    assert "..." in result2
    assert len(result2) < 120


def test_todo_repr_all_newlines_bounded() -> None:
    """repr(Todo) with text of all newlines should stay bounded."""
    # 100 newlines = 100 raw chars, but 200+ escaped chars
    text = "\n" * 100
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # repr output should never exceed 120 chars total
    assert len(result) < 120, f"repr too long: {len(result)} chars - {result}"
    assert "..." in result  # Should be truncated
