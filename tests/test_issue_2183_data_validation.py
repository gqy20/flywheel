"""Tests for data validation and schema verification (Issue #2183).

These tests verify that:
1. save() rejects lists with duplicate todo IDs
2. save() rejects todos with missing required fields
3. Valid data passes validation
4. Error messages include duplicate ID details
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_rejects_duplicate_ids(tmp_path) -> None:
    """save() should reject list with duplicate todo IDs."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create todos with duplicate IDs
    todos = [
        Todo(id=1, text="first task"),
        Todo(id=2, text="second task"),
        Todo(id=1, text="duplicate id task"),  # Duplicate ID
    ]

    # Should raise ValueError with clear message about duplicate ID
    with pytest.raises(ValueError, match=r"(?i)duplicate"):
        storage.save(todos)


def test_save_duplicate_id_error_includes_details(tmp_path) -> None:
    """Validation error should include the problematic ID in message."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=5, text="task one"),
        Todo(id=5, text="task two"),  # Duplicate
    ]

    with pytest.raises(ValueError, match=r"5"):
        storage.save(todos)


def test_save_rejects_missing_required_field_via_dict_manipulation(tmp_path) -> None:
    """save() should validate required fields are present.

    This test creates a valid Todo, then manipulates its internal state
    to simulate data corruption, verifying that save() catches this.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create a todo and then corrupt it by setting text to empty
    # (which violates the implicit contract that text should be non-empty)
    todo = Todo(id=1, text="valid task")
    todo.text = ""  # Empty text should be rejected

    with pytest.raises(ValueError, match=r"text|empty|required"):
        storage.save([todo])


def test_save_valid_data_passes_validation(tmp_path) -> None:
    """Valid todo data should pass validation and save successfully."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task one"),
        Todo(id=2, text="task two"),
        Todo(id=3, text="task three", done=True),
    ]

    # Should not raise any exception
    storage.save(todos)

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 3
    assert [t.id for t in loaded] == [1, 2, 3]


def test_validate_is_overridable_for_extensibility(tmp_path) -> None:
    """validate() method should be overridable for custom validation logic.

    This allows subclasses to add custom validation rules.
    """
    db = tmp_path / "custom.json"

    class CustomStorage(TodoStorage):
        """Custom storage with additional validation rules."""

        def validate(self, todos: list[Todo]) -> None:
            """Call parent validation plus custom rules."""
            super().validate(todos)
            # Custom rule: reject tasks with 'forbidden' in text
            for todo in todos:
                if "forbidden" in todo.text.lower():
                    raise ValueError(
                        f"Todo {todo.id} contains forbidden word: {todo.text}"
                    )

    storage = CustomStorage(str(db))

    # Should reject forbidden content
    todos = [Todo(id=1, text="this has forbidden content")]
    with pytest.raises(ValueError, match=r"forbidden"):
        storage.save(todos)

    # Should allow normal content
    valid_todos = [Todo(id=1, text="normal task")]
    storage.save(valid_todos)
    loaded = storage.load()
    assert len(loaded) == 1
