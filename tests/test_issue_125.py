"""Tests for issue #125 - next_id calculation with duplicate IDs."""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_load_old_format_with_duplicate_ids():
    """Test that loading old format with duplicate IDs calculates next_id correctly.

    Issue #125: When loading old format data with duplicate IDs, the next_id
    calculation should still work correctly. The fix uses set() to deduplicate
    IDs before calculating max.
    """
    # Create a temporary file with old format data containing duplicate IDs
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        old_data = [
            {"id": 1, "title": "Task 1", "status": "pending"},
            {"id": 2, "title": "Task 2", "status": "pending"},
            {"id": 2, "title": "Task 2 Duplicate", "status": "pending"},  # Duplicate ID
            {"id": 3, "title": "Task 3", "status": "pending"},
        ]
        json.dump(old_data, f)
        temp_path = f.name

    try:
        # Load the storage with duplicate IDs
        storage = Storage(path=temp_path)

        # The next_id should be 4 (max of {1, 2, 3} + 1)
        # Even though valid_ids contains [1, 2, 2, 3], using set() gives {1, 2, 3}
        assert storage.get_next_id() == 4, (
            f"Expected next_id to be 4, but got {storage.get_next_id()}. "
            "This indicates that duplicate IDs were not properly handled."
        )

        # Verify that all valid todos were loaded (including duplicates)
        todos = storage.list()
        assert len(todos) == 4, f"Expected 4 todos, but got {len(todos)}"

    finally:
        # Clean up
        Path(temp_path).unlink(missing_ok=True)


def test_load_old_format_with_invalid_items_and_duplicates():
    """Test loading old format with both invalid items and duplicate IDs.

    This test ensures that the combination of skipping invalid items and
    handling duplicate IDs works correctly.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        old_data = [
            {"id": 1, "title": "Task 1", "status": "pending"},
            {"id": 1, "title": "Task 1 Duplicate", "status": "pending"},  # Duplicate
            {"invalid": "data"},  # Invalid item (no 'id' field)
            {"id": 3, "title": "Task 3", "status": "pending"},
            None,  # Invalid item (not a dict)
            {"id": 3, "title": "Task 3 Duplicate", "status": "pending"},  # Duplicate
        ]
        json.dump(old_data, f)
        temp_path = f.name

    try:
        storage = Storage(path=temp_path)

        # The next_id should be 4 (max of {1, 3} + 1)
        # Even with duplicate IDs, after deduplication the max should be 3
        assert storage.get_next_id() == 4, (
            f"Expected next_id to be 4, but got {storage.get_next_id()}"
        )

        # Only valid todos should be loaded
        todos = storage.list()
        assert len(todos) == 5, f"Expected 5 valid todos, but got {len(todos)}"

    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_load_old_format_empty_list():
    """Test loading old format with empty list."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        old_data = []
        json.dump(old_data, f)
        temp_path = f.name

    try:
        storage = Storage(path=temp_path)
        assert storage.get_next_id() == 1, "Expected next_id to be 1 for empty list"
        assert storage.list() == [], "Expected no todos"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_add_todo_after_loading_duplicate_ids():
    """Test that adding a new todo after loading data with duplicate IDs works correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        old_data = [
            {"id": 1, "title": "Task 1", "status": "pending"},
            {"id": 1, "title": "Task 1 Duplicate", "status": "pending"},  # Duplicate
            {"id": 5, "title": "Task 5", "status": "pending"},
        ]
        json.dump(old_data, f)
        temp_path = f.name

    try:
        storage = Storage(path=temp_path)

        # Add a new todo without specifying ID
        new_todo = Todo(title="New Task", status="pending")
        added_todo = storage.add(new_todo)

        # The new todo should get ID 6 (max of {1, 5} + 1)
        assert added_todo.id == 6, f"Expected new todo ID to be 6, but got {added_todo.id}"
        assert storage.get_next_id() == 7, f"Expected next_id to be 7, but got {storage.get_next_id()}"

    finally:
        Path(temp_path).unlink(missing_ok=True)
