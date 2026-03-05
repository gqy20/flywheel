"""Tests for Todo.__repr__ quote escaping at truncation boundary (Issue #7301).

These tests verify that:
1. Todo repr output is valid Python syntax even with quotes at truncation boundary
2. Truncated text with quotes produces parseable repr output
3. The repr format remains intact when truncation occurs near special characters
"""

from __future__ import annotations

import ast

from flywheel.todo import Todo


def test_todo_repr_with_quotes_at_truncation_boundary() -> None:
    """repr(Todo) should produce valid syntax when quotes are at truncation boundary.

    Issue #7301: When text is truncated, quotes in the truncated portion should
    be properly escaped to maintain valid repr format.
    """
    # Create text with quote near position 47 (where truncation happens)
    # Text is longer than 50 chars, so it will be truncated
    text_with_quote_at_46 = "a" * 46 + '"' + "b" * 60
    todo = Todo(id=1, text=text_with_quote_at_46)
    result = repr(todo)

    # The repr output should be valid Python syntax
    try:
        ast.parse(result, mode="eval")
    except SyntaxError as e:
        raise AssertionError(
            f"repr output is not valid Python syntax: {result}"
        ) from e


def test_todo_repr_with_mixed_quotes_truncated() -> None:
    """repr(Todo) should handle mixed quotes in truncated text."""
    # Text with both single and double quotes that will be truncated
    text = 'He said: "I\'m going to the store" and then continued with more text'
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should be valid Python syntax
    ast.parse(result, mode="eval")

    # Should contain truncation indicator
    assert "..." in result


def test_todo_repr_short_text_with_quotes_is_parseable() -> None:
    """Todo with text containing quotes should produce parseable repr (Issue #7301)."""
    todo = Todo(id=1, text='He said "hello"')
    result = repr(todo)

    # Should be valid Python syntax
    ast.parse(result, mode="eval")

    # Should contain the expected text representation
    assert "He said" in result
    assert "hello" in result


def test_todo_repr_truncated_text_format_intact() -> None:
    """Truncated text with quotes should maintain repr format integrity."""
    # Create a long text (> 50 chars) with quotes near the truncation point
    long_text = 'This is a test "with quotes" near position forty-seven and continues'
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be valid Python syntax
    ast.parse(result, mode="eval")

    # Verify format: should start with Todo( and end with done=...)
    assert result.startswith("Todo(")
    assert "id=" in result
    assert "text=" in result
    assert "done=" in result
