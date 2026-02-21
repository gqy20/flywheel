"""Tests for issue #4930: next_id should not generate duplicate IDs.

Bug description: next_id can generate duplicate IDs if loaded data contains
non-sequential or negative IDs. The current implementation uses max() + 1,
which can produce IDs that already exist in the list.

This test suite verifies:
1. next_id never returns an ID that already exists in the todos list
2. Negative IDs in loaded data don't cause issues with ID generation
3. Non-sequential IDs don't cause collisions
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_non_sequential_ids(tmp_path) -> None:
    """Test that next_id doesn't collide with non-sequential IDs.

    Given IDs [1, 5, 10], next_id should return 11, not a collision.
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create todos with non-sequential IDs
    todos = [
        Todo(id=1, text="first"),
        Todo(id=5, text="fifth"),
        Todo(id=10, text="tenth"),
    ]
    storage.save(todos)

    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # next_id should be 11 (max + 1)
    assert next_id == 11
    # Verify it doesn't collide
    existing_ids = {t.id for t in loaded}
    assert next_id not in existing_ids


def test_next_id_with_negative_ids_no_collision(tmp_path) -> None:
    """Test that negative IDs in JSON are rejected during load.

    With the fix, negative IDs are rejected at Todo.from_dict level,
    preventing them from being loaded at all.
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON data with a negative ID directly (bypassing Todo validation)
    invalid_data = [
        {"id": 1, "text": "first"},
        {"id": -1, "text": "negative"},
        {"id": 5, "text": "fifth"},
    ]
    db.write_text(json.dumps(invalid_data), encoding="utf-8")

    # Loading should fail because negative IDs are now rejected
    with pytest.raises(ValueError, match="positive"):
        storage.load()


def test_next_id_with_all_negative_ids_rejected(tmp_path) -> None:
    """Test that JSON with all negative IDs is rejected during load.

    With the fix, all negative IDs are rejected at Todo.from_dict level.
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON data with only negative IDs directly
    invalid_data = [
        {"id": -5, "text": "negative five"},
        {"id": -10, "text": "negative ten"},
    ]
    db.write_text(json.dumps(invalid_data), encoding="utf-8")

    # Loading should fail because negative IDs are now rejected
    with pytest.raises(ValueError, match="positive"):
        storage.load()


def test_next_id_always_returns_unused_id(tmp_path) -> None:
    """Test that next_id never returns an ID that already exists.

    This is the fundamental requirement: next_id must always return
    a unique ID, regardless of the existing ID patterns.
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Test various ID patterns (only positive IDs since negative are rejected)
    test_cases = [
        [1, 2, 3],  # Sequential
        [1, 5, 10],  # Sparse
        [100, 200, 300],  # Large IDs
    ]

    for ids in test_cases:
        # Create todos with these IDs
        todos = [Todo(id=i, text=f"todo-{i}") for i in ids]
        storage.save(todos)

        loaded = storage.load()
        next_id = storage.next_id(loaded)
        existing_ids = {t.id for t in loaded}

        # CRITICAL: next_id must not collide with existing IDs
        assert next_id not in existing_ids, (
            f"next_id={next_id} collides with existing IDs {existing_ids}"
        )

        # next_id should be positive
        assert next_id > 0, f"next_id should be positive, got {next_id}"


def test_negative_id_rejected_in_from_dict() -> None:
    """Test that Todo.from_dict rejects negative IDs.

    Per the fix suggestion in the issue, IDs should be validated
    to be positive integers in from_dict.
    """
    with pytest.raises(ValueError, match="positive"):
        Todo.from_dict({"id": -1, "text": "negative id todo"})


def test_zero_id_rejected_in_from_dict() -> None:
    """Test that Todo.from_dict rejects zero as an ID.

    Zero is technically not positive, so it should also be rejected.
    """
    with pytest.raises(ValueError, match="positive"):
        Todo.from_dict({"id": 0, "text": "zero id todo"})


def test_positive_id_accepted_in_from_dict() -> None:
    """Test that Todo.from_dict accepts positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.id == 1

    todo = Todo.from_dict({"id": 100, "text": "another valid todo"})
    assert todo.id == 100


def test_next_id_with_empty_list() -> None:
    """Test that next_id returns 1 for an empty todo list."""
    storage = TodoStorage("/nonexistent/path.json")
    next_id = storage.next_id([])
    assert next_id == 1
