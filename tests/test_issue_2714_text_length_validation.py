"""Tests for Todo text length validation (Issue #2714).

These tests verify that:
1. Todo.text length is bounded by MAX_TODO_TEXT_LENGTH
2. Todo.rename() raises ValueError if text exceeds max length
3. Todo.from_dict() raises ValueError if text exceeds max length
4. TodoApp.add() raises ValueError if text exceeds max length
5. Text at exactly the limit is accepted
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo

# Import the constant we're about to add - will fail until implemented
try:
    from flywheel.todo import MAX_TODO_TEXT_LENGTH
except ImportError:
    # Fallback for RED stage - the constant doesn't exist yet
    MAX_TODO_TEXT_LENGTH = 10000


def test_todo_text_at_limit_succeeds() -> None:
    """Todo with text exactly at MAX_TODO_TEXT_LENGTH should be accepted."""
    # Create text at exactly the limit
    text_at_limit = "x" * MAX_TODO_TEXT_LENGTH
    todo = Todo(id=1, text=text_at_limit)
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH
    assert todo.text == text_at_limit


def test_todo_text_exceeding_limit_raises_value_error() -> None:
    """Todo with text exceeding MAX_TODO_TEXT_LENGTH should raise ValueError."""
    text_too_long = "x" * (MAX_TODO_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        Todo(id=1, text=text_too_long)


def test_todo_rename_at_limit_succeeds() -> None:
    """Todo.rename() with text exactly at limit should succeed."""
    todo = Todo(id=1, text="original")
    text_at_limit = "y" * MAX_TODO_TEXT_LENGTH
    todo.rename(text_at_limit)
    assert todo.text == text_at_limit


def test_todo_rename_exceeding_limit_raises_value_error() -> None:
    """Todo.rename() should raise ValueError if text exceeds max length."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at
    text_too_long = "y" * (MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        todo.rename(text_too_long)

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_from_dict_at_limit_succeeds() -> None:
    """Todo.from_dict() with text exactly at limit should succeed."""
    text_at_limit = "z" * MAX_TODO_TEXT_LENGTH
    todo = Todo.from_dict({"id": 1, "text": text_at_limit})
    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH


def test_todo_from_dict_exceeding_limit_raises_value_error() -> None:
    """Todo.from_dict() should raise ValueError if text exceeds max length."""
    text_too_long = "z" * (MAX_TODO_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        Todo.from_dict({"id": 1, "text": text_too_long})


def test_todo_app_add_at_limit_succeeds(tmp_path) -> None:
    """TodoApp.add() with text exactly at limit should succeed."""
    app = TodoApp(str(tmp_path / "db.json"))
    text_at_limit = "w" * MAX_TODO_TEXT_LENGTH

    todo = app.add(text_at_limit)
    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH

    # Verify it persists
    loaded = app.list()
    assert len(loaded) == 1
    assert loaded[0].text == text_at_limit


def test_todo_app_add_exceeding_limit_raises_value_error(tmp_path) -> None:
    """TodoApp.add() should raise ValueError if text exceeds max length."""
    app = TodoApp(str(tmp_path / "db.json"))
    text_too_long = "w" * (MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        app.add(text_too_long)

    # Verify no todo was created
    assert app.list() == []


def test_storage_load_with_text_at_limit(tmp_path) -> None:
    """Storage should be able to load and save todos with text at limit."""
    db = tmp_path / "db.json"
    storage = TodoStorage(str(db))

    # Create todo with text at limit
    text_at_limit = "v" * MAX_TODO_TEXT_LENGTH
    todos = [Todo(id=1, text=text_at_limit)]
    storage.save(todos)

    # Load and verify
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == text_at_limit
    assert len(loaded[0].text) == MAX_TODO_TEXT_LENGTH


def test_storage_load_rejects_text_exceeding_limit(tmp_path) -> None:
    """Storage.load() should raise ValueError if any todo text exceeds limit."""
    db = tmp_path / "db.json"
    storage = TodoStorage(str(db))

    # Manually write JSON with oversized text (bypassing Todo constructor)
    import json

    text_too_long = "u" * (MAX_TODO_TEXT_LENGTH + 1)
    db.write_text(
        json.dumps([{"id": 1, "text": text_too_long, "done": False}]),
        encoding="utf-8",
    )

    # Should raise ValueError when loading
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        storage.load()


def test_error_message_is_clear_and_actionable() -> None:
    """Error message should clearly state the limit and current length."""
    text_too_long = "x" * (MAX_TODO_TEXT_LENGTH + 100)
    try:
        Todo(id=1, text=text_too_long)
        raise AssertionError("Expected ValueError for oversized text")
    except ValueError as e:
        error_msg = str(e).lower()
        # Error should mention the limit
        assert "max" in error_msg or "limit" in error_msg or "length" in error_msg
        # Error should be actionable
        assert "too long" in error_msg or "exceeds" in error_msg or "maximum" in error_msg


def test_multibyte_unicode_chars_counted_correctly() -> None:
    """Length validation should count characters, not bytes."""
    # Each emoji is a single character (Python counts code points)
    emoji = "😀"
    single_char_text = emoji * MAX_TODO_TEXT_LENGTH
    todo = Todo(id=1, text=single_char_text)
    # Should succeed because we have exactly MAX_TODO_TEXT_LENGTH characters
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH

    # One extra character should fail
    text_too_long = emoji * (MAX_TODO_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        Todo(id=1, text=text_too_long)


def test_whitespace_stripped_before_length_check() -> None:
    """Length check should apply to stripped text, not raw input."""
    todo = Todo(id=1, text="original")

    # Text with padding that is at limit after stripping should succeed
    # " " + "y" * 10000 + " " becomes "y" * 10000 after stripping (exactly at limit)
    text_at_limit_with_padding = " " + "y" * MAX_TODO_TEXT_LENGTH + " "
    todo.rename(text_at_limit_with_padding)
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH
    assert todo.text == "y" * MAX_TODO_TEXT_LENGTH

    # Text with padding that would exceed limit after stripping should fail
    # "  " + "z" * 10000 + "  " becomes "z" * 10000 after stripping, but if we add
    # one more char it would exceed the limit
    text_exceeding_with_padding = "  " + "z" * (MAX_TODO_TEXT_LENGTH + 1) + "  "
    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*length|max.*length"):
        todo.rename(text_exceeding_with_padding)

    # Verify state unchanged after failed validation
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH
