"""Tests for data validation and schema verification (Issue #2183).

These tests verify that:
1. save() validates todo list integrity (duplicate IDs, invalid fields)
2. validate() checks for duplicate todo IDs
3. validate() checks all required fields are present
4. Validation errors are descriptive (include problematic ID/field)
5. Valid data passes validation
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_rejects_duplicate_ids(tmp_path) -> None:
    """save() should reject list with duplicate IDs."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create todos with duplicate IDs
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo"),
        Todo(id=1, text="duplicate id todo"),
    ]

    # Should raise ValueError with clear error about duplicate IDs
    with pytest.raises(ValueError, match=r"Duplicate.*ID|duplicate.*id"):
        storage.save(todos)


def test_save_rejects_missing_required_fields(tmp_path) -> None:
    """save() should reject todos with missing required fields.

    Note: This test documents current behavior. Individual Todo validation
    happens in from_dict(), but we should also catch it at save() time.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Try to save a Todo with empty text (should be rejected)
    # First verify that Todo with empty text can be created but not saved
    todo = Todo(id=1, text="")
    # The Todo itself may allow empty text, but save should catch invalid data

    # If we create a todo with invalid state, save should validate
    # This is a defensive check - we want to ensure save() validates
    # even if individual Todo objects were created with invalid state
    todos = [todo]

    # Should raise ValueError about invalid/missing required fields
    with pytest.raises(ValueError, match=r"required|field|empty|invalid"):
        storage.save(todos)


def test_save_accepts_valid_data(tmp_path) -> None:
    """save() should accept valid todos with unique IDs and all required fields."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo", done=False),
        Todo(id=2, text="second todo", done=True),
        Todo(id=3, text="third todo"),
    ]

    # Should not raise any errors
    storage.save(todos)

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].id == 1
    assert loaded[1].id == 2
    assert loaded[2].id == 3
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[2].text == "third todo"


def test_validation_error_includes_duplicate_id_details(tmp_path) -> None:
    """Validation error should include details about which ID is duplicated."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=1, text="duplicate"),
    ]

    with pytest.raises(ValueError) as exc_info:
        storage.save(todos)

    # Error message should mention the problematic ID
    error_msg = str(exc_info.value).lower()
    assert "1" in error_msg or "duplicate" in error_msg


def test_save_empty_list_is_valid(tmp_path) -> None:
    """save() should accept an empty list (valid state for new db)."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Empty list is valid
    storage.save([])

    # Should be able to load empty list
    loaded = storage.load()
    assert loaded == []


def test_validate_method_checks_duplicate_ids(tmp_path) -> None:
    """validate() method should detect duplicate IDs."""
    storage = TodoStorage(str(tmp_path / "test.json"))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="duplicate"),
    ]

    # validate() should raise ValueError for duplicates
    with pytest.raises(ValueError, match=r"Duplicate"):
        storage.validate(todos)


def test_validate_method_accepts_valid_todos(tmp_path) -> None:
    """validate() method should pass for valid todos."""
    storage = TodoStorage(str(tmp_path / "test.json"))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
    ]

    # validate() should not raise for valid data
    storage.validate(todos)  # No exception means pass
