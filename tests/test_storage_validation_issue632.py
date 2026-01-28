"""Tests for data validation and repair mechanism (Issue #632).

This module tests the data validation and repair functionality that:
1. Validates unique IDs
2. Validates field types
3. Attempts auto-repair (deduplication) when corruption is detected
4. Renames corrupted files to .bak and creates new file when repair fails
"""
import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


@pytest.fixture
def temp_storage_path():
    """Create a temporary file path for testing."""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)
    # Also clean up any backup files
    if os.path.exists(path + '.bak'):
        os.remove(path + '.bak')
    if os.path.exists(path + '.backup'):
        os.remove(path + '.backup')


@pytest.mark.asyncio
async def test_load_with_duplicate_ids_should_detect_and_repair():
    """Test that duplicate IDs are detected and auto-repaired during load."""
    storage = FileStorage(temp_storage_path())

    # Create data with duplicate IDs
    data = {
        "todos": [
            {"id": 1, "title": "Todo 1", "status": "pending"},
            {"id": 2, "title": "Todo 2", "status": "pending"},
            {"id": 1, "title": "Duplicate Todo 1", "status": "completed"},  # Duplicate ID
        ],
        "metadata": {"checksum": None},
        "next_id": 3
    }

    # Write the data to file
    with open(storage.path, 'w') as f:
        json.dump(data, f)

    # Load the storage - should detect and repair duplicate IDs
    await storage._load()

    # Verify that duplicates were removed
    todos = storage.list()
    assert len(todos) == 2, "Duplicate IDs should be removed during load"

    # Verify that all IDs are unique
    todo_ids = [todo.id for todo in todos]
    assert len(todo_ids) == len(set(todo_ids)), "All todo IDs should be unique"

    # Verify that the first occurrence is kept
    assert any(todo.title == "Todo 1" for todo in todos), "First occurrence should be kept"
    assert any(todo.title == "Todo 2" for todo in todos), "Second todo should be preserved"


@pytest.mark.asyncio
async def test_load_with_invalid_field_types_should_detect_and_repair():
    """Test that invalid field types are detected and auto-repaired during load."""
    storage = FileStorage(temp_storage_path())

    # Create data with invalid field types
    data = {
        "todos": [
            {"id": 1, "title": "Valid Todo", "status": "pending"},
            {"id": "invalid", "title": "Invalid ID Type", "status": "pending"},  # Invalid ID type
            {"id": 2, "title": 12345, "status": "pending"},  # Invalid title type
            {"id": 3, "title": "Valid Todo 2", "status": "unknown"},  # Invalid status
        ],
        "metadata": {"checksum": None},
        "next_id": 4
    }

    # Write the data to file
    with open(storage.path, 'w') as f:
        json.dump(data, f)

    # Load the storage - should detect and skip invalid todos
    await storage._load()

    # Verify that only valid todos remain
    todos = storage.list()
    assert len(todos) >= 1, "At least the valid todo should remain"

    # Verify all loaded todos have correct field types
    for todo in todos:
        assert isinstance(todo.id, int), "ID should be an integer"
        assert isinstance(todo.title, str), "Title should be a string"
        assert isinstance(todo.status, str), "Status should be a string"


@pytest.mark.asyncio
async def test_load_with_severe_corruption_should_create_bak_file():
    """Test that severely corrupted files are renamed to .bak and new file is created."""
    storage = FileStorage(temp_storage_path())

    # Create severely corrupted JSON (invalid structure)
    with open(storage.path, 'w') as f:
        f.write('{ invalid json content }')

    # Load the storage - should create backup and reset
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        await storage._load()

    # Verify backup file was created with .bak extension
    backup_path = str(storage.path) + '.bak'
    assert os.path.exists(backup_path), f"Backup file should be created at {backup_path}"

    # Also check for .backup file (current implementation uses .backup)
    backup_path_alt = str(storage.path) + '.backup'
    # At least one backup file should exist
    assert os.path.exists(backup_path) or os.path.exists(backup_path_alt), \
        "Backup file should be created"


@pytest.mark.asyncio
async def test_load_with_all_duplicate_ids_should_keep_at_least_one():
    """Test that when all todos have duplicate IDs, at least one is kept."""
    storage = FileStorage(temp_storage_path())

    # Create data where all todos have the same ID
    data = {
        "todos": [
            {"id": 1, "title": "Todo 1", "status": "pending"},
            {"id": 1, "title": "Todo 2", "status": "pending"},
            {"id": 1, "title": "Todo 3", "status": "pending"},
        ],
        "metadata": {"checksum": None},
        "next_id": 2
    }

    # Write the data to file
    with open(storage.path, 'w') as f:
        json.dump(data, f)

    # Load the storage
    await storage._load()

    # Verify that at least one todo remains
    todos = storage.list()
    assert len(todos) == 1, "Only one todo should remain when all have duplicate IDs"

    # Verify the kept todo has the correct ID
    assert todos[0].id == 1, "The kept todo should have ID 1"


@pytest.mark.asyncio
async def test_load_preserves_data_integrity():
    """Test that data validation doesn't corrupt valid data."""
    storage = FileStorage(temp_storage_path())

    # Create valid data
    data = {
        "todos": [
            {"id": 1, "title": "Todo 1", "status": "pending"},
            {"id": 2, "title": "Todo 2", "status": "completed"},
            {"id": 3, "title": "Todo 3", "status": "pending"},
        ],
        "metadata": {"checksum": None},
        "next_id": 4
    }

    # Write the data to file
    with open(storage.path, 'w') as f:
        json.dump(data, f)

    # Load the storage
    await storage._load()

    # Verify all todos are loaded correctly
    todos = storage.list()
    assert len(todos) == 3, "All valid todos should be loaded"

    # Verify all data is preserved
    todo_dict = {todo.id: todo for todo in todos}
    assert todo_dict[1].title == "Todo 1"
    assert todo_dict[2].title == "Todo 2"
    assert todo_dict[3].title == "Todo 3"
    assert todo_dict[2].status == "completed"
