"""Tests for next_id() edge cases and duplicate ID handling.

This test suite provides coverage for missing test cases identified in issue #4987:
- next_id() with gap IDs [1,5,10] -> should return 11 (max+1)
- load() with duplicate IDs in JSON file
- next_id() with single high ID
- next_id() after removing middle item
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_gap_ids_returns_max_plus_one(tmp_path) -> None:
    """Test next_id() returns max_id + 1 when there are gaps in IDs.

    With IDs [1, 5, 10], the next ID should be 11 (max+1), not 6.
    The storage layer does not fill gaps - it always returns max+1.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with gaps in IDs
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth"), Todo(id=10, text="tenth")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 3

    # next_id should return max(1, 5, 10) + 1 = 11
    next_id = storage.next_id(loaded)
    assert next_id == 11


def test_next_id_with_single_high_id(tmp_path) -> None:
    """Test next_id() correctly handles a large gap between first and second ID.

    With IDs [1, 100], the next ID should be 101.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first"), Todo(id=100, text="hundredth")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2

    # next_id should return max(1, 100) + 1 = 101
    next_id = storage.next_id(loaded)
    assert next_id == 101


def test_load_accepts_duplicate_ids_in_json(tmp_path) -> None:
    """Test load() accepts JSON with duplicate IDs.

    The storage layer does not enforce ID uniqueness - it simply loads
    whatever is in the JSON file. Duplicate IDs are allowed in storage.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create JSON with duplicate IDs
    duplicate_data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 1, "text": "second todo with same id", "done": True},
        {"id": 2, "text": "third todo", "done": False},
    ]
    db.write_text(json.dumps(duplicate_data), encoding="utf-8")

    # load() should return all items, including duplicates
    loaded = storage.load()
    assert len(loaded) == 3

    # Verify both items with id=1 are present
    id_1_items = [t for t in loaded if t.id == 1]
    assert len(id_1_items) == 2
    assert id_1_items[0].text == "first todo"
    assert id_1_items[1].text == "second todo with same id"

    # Verify the item with id=2 is also present
    id_2_items = [t for t in loaded if t.id == 2]
    assert len(id_2_items) == 1


def test_next_id_after_removing_middle_item(tmp_path) -> None:
    """Test next_id() returns correct value after removing a middle item.

    After removing item with id=2 from [1, 2, 3], next_id should return 4
    (max+1), not 2 (to fill the gap).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create three todos
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    storage.save(todos)

    # Load and remove the middle one
    loaded = storage.load()
    remaining = [t for t in loaded if t.id != 2]
    storage.save(remaining)

    # Verify removal
    reloaded = storage.load()
    assert len(reloaded) == 2
    assert [t.id for t in reloaded] == [1, 3]

    # next_id should return max(1, 3) + 1 = 4, not 2
    next_id = storage.next_id(reloaded)
    assert next_id == 4


def test_next_id_with_empty_list_returns_one(tmp_path) -> None:
    """Test next_id() returns 1 for an empty list."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    # Empty list should return 1
    next_id = storage.next_id([])
    assert next_id == 1


def test_next_id_with_negative_ids(tmp_path) -> None:
    """Test next_id() handles negative IDs correctly.

    While negative IDs are unusual, the storage layer does not prevent them.
    next_id() should return max + 1, which could be 0 if max is -1.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create JSON with a negative ID (directly, bypassing normal save)
    negative_data = [
        {"id": -1, "text": "negative id todo", "done": False},
        {"id": -5, "text": "another negative", "done": False},
    ]
    db.write_text(json.dumps(negative_data), encoding="utf-8")

    loaded = storage.load()
    assert len(loaded) == 2

    # next_id should return max(-1, -5) + 1 = 0
    next_id = storage.next_id(loaded)
    assert next_id == 0
