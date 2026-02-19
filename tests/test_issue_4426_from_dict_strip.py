"""Tests for from_dict() text stripping behavior (Issue #4426).

These tests verify that:
1. from_dict() strips leading/trailing whitespace from text
2. This is consistent with CLI.add() and rename() behavior
3. Roundtrip save/load preserves stripped text
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_from_dict_strips_leading_whitespace() -> None:
    """from_dict() should strip leading whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  hello"})
    assert todo.text == "hello", f"Expected stripped text 'hello', got {todo.text!r}"


def test_from_dict_strips_trailing_whitespace() -> None:
    """from_dict() should strip trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "hello  "})
    assert todo.text == "hello", f"Expected stripped text 'hello', got {todo.text!r}"


def test_from_dict_strips_both_whitespace() -> None:
    """from_dict() should strip both leading and trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  hello  "})
    assert todo.text == "hello", f"Expected stripped text 'hello', got {todo.text!r}"


def test_from_dict_strips_tabs_and_newlines() -> None:
    """from_dict() should strip tabs and newlines from text edges."""
    todo = Todo.from_dict({"id": 1, "text": "\t\n  hello  \n\t"})
    assert todo.text == "hello", f"Expected stripped text 'hello', got {todo.text!r}"


def test_from_dict_preserves_internal_whitespace() -> None:
    """from_dict() should preserve whitespace between words."""
    todo = Todo.from_dict({"id": 1, "text": "  hello world  "})
    assert todo.text == "hello world", f"Expected 'hello world', got {todo.text!r}"


def test_from_dict_strips_text_consistent_with_rename() -> None:
    """from_dict() stripping should be consistent with rename() behavior."""
    # Create a todo via from_dict with padded text
    todo = Todo.from_dict({"id": 1, "text": "  task  "})
    assert todo.text == "task"

    # Rename with padded text should produce same result
    todo.rename("  new task  ")
    assert todo.text == "new task"


def test_storage_load_preserves_stripped_text(tmp_path) -> None:
    """Save then load should preserve stripped text state."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create todo with stripped text
    original = Todo(id=1, text="  original task  ")
    storage.save([original])

    # Load and verify text is stripped
    loaded = storage.load()
    assert len(loaded) == 1
    # The text should be stripped during from_dict when loading
    assert loaded[0].text == "original task", f"Expected stripped text, got {loaded[0].text!r}"
