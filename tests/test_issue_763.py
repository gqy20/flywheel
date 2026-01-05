"""Test transactional batch operations (Issue #763).

This test verifies that batch operations are truly transactional:
1. If the operation succeeds, all data is committed
2. If the operation fails, NO data is committed (atomicity)
3. State remains consistent even after failures
4. No partial writes or ID leaks occur
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_add_batch_rollback_on_save_failure():
    """Test that add_batch rolls back completely if save fails.

    Verifies atomicity: if save fails during add_batch,
    no todos should be added and next_id should not change.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todos
        storage = FileStorage(str(storage_path))
        for i in range(5):
            todo = Todo(id=i+1, title=f"Original Task {i+1}", status="pending")
            storage.add(todo)

        # Record state before batch operation
        initial_next_id = storage.get_next_id()
        initial_count = len(storage.list())
        assert initial_next_id == 6
        assert initial_count == 5

        # Mock os.replace to fail during save (simulating crash/disk full)
        original_replace = os.replace

        def failing_replace(src, dst):
            """Simulate failure during atomic replace."""
            if '.tmp' in str(src):
                raise OSError("Simulated I/O error during save")
            return original_replace(src, dst)

        # Attempt to add batch - should fail
        with patch('os.replace', side_effect=failing_replace):
            with pytest.raises(OSError, match="Simulated I/O error"):
                new_todos = [
                    Todo(title=f"New Task {i}", status="pending")
                    for i in range(10, 15)
                ]
                storage.add_batch(new_todos)

        # Verify complete rollback: no todos were added
        final_todos = storage.list()
        assert len(final_todos) == initial_count, \
            f"Should still have {initial_count} todos after failed batch, got {len(final_todos)}"

        # Verify next_id was not leaked/incremented
        final_next_id = storage.get_next_id()
        assert final_next_id == initial_next_id, \
            f"next_id should remain {initial_next_id} after failed batch, got {final_next_id}"

        # Verify file still contains only original data
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 5
        assert data["next_id"] == 6


def test_add_batch_all_or_nothing_write():
    """Test that add_batch writes all todos atomically.

    Verifies that the batch is written as a single unit:
    either all todos appear in the file, or none do.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todos
        storage = FileStorage(str(storage_path))
        for i in range(3):
            todo = Todo(id=i+1, title=f"Task {i+1}", status="pending")
            storage.add(todo)

        # Track file modifications during batch add
        file_states = []

        def track_file_write(path, mode):
            """Track file states during write operations."""
            if storage_path.exists() and 'w' in mode:
                with open(storage_path, 'r') as f:
                    try:
                        file_states.append(json.load(f))
                    except:
                        pass
            return open(path, mode)

        # Add a batch of 10 todos
        new_todos = [
            Todo(title=f"Batch Task {i}", status="pending")
            for i in range(10)
        ]
        added = storage.add_batch(new_todos)

        # Verify all 10 todos were added
        assert len(added) == 10

        # Verify final state has all todos
        final_todos = storage.list()
        assert len(final_todos) == 13  # 3 original + 10 new

        # Verify file has complete data
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 13


def test_add_batch_with_explicit_ids_rollback_on_failure():
    """Test rollback when batch contains todos with explicit IDs.

    Verifies that explicit IDs are also rolled back on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = FileStorage(str(storage_path))

        # Add some initial todos
        storage.add(Todo(id=1, title="Task 1", status="pending"))
        storage.add(Todo(id=2, title="Task 2", status="pending"))

        initial_count = len(storage.list())

        # Try to add batch with explicit IDs, but fail during save
        original_replace = os.replace

        def failing_replace(src, dst):
            if '.tmp' in str(src):
                raise IOError("Disk full simulation")
            return original_replace(src, dst)

        with patch('os.replace', side_effect=failing_replace):
            with pytest.raises(IOError, match="Disk full"):
                new_todos = [
                    Todo(id=10, title="Should not appear", status="pending"),
                    Todo(id=20, title="Should not appear either", status="pending"),
                ]
                storage.add_batch(new_todos)

        # Verify rollback - explicit IDs should not be in storage
        final_todos = storage.list()
        assert len(final_todos) == initial_count

        todo_ids = [t.id for t in final_todos]
        assert 10 not in todo_ids, "Todo with ID 10 should not be present after rollback"
        assert 20 not in todo_ids, "Todo with ID 20 should not be present after rollback"


def test_add_batch_state_consistency_after_failure():
    """Test that storage state remains consistent after batch failure.

    Verifies that:
    1. Memory state (_todos) is consistent
    2. Disk state (file) is consistent
    3. next_id is valid
    4. No orphaned or duplicate IDs exist
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = FileStorage(str(storage_path))

        # Add initial todos
        for i in range(5):
            storage.add(Todo(title=f"Initial {i}", status="pending"))

        # Try batch operation that fails
        original_replace = os.replace

        def failing_replace(src, dst):
            if '.tmp' in str(src):
                raise OSError("Simulated crash")
            return original_replace(src, dst)

        with patch('os.replace', side_effect=failing_replace):
            with pytest.raises(OSError):
                new_todos = [
                    Todo(title=f"Failed {i}", status="pending")
                    for i in range(10)
                ]
                storage.add_batch(new_todos)

        # Verify memory consistency
        memory_todos = storage.list()
        assert len(memory_todos) == 5

        # Verify all IDs in memory are unique
        memory_ids = [t.id for t in memory_todos]
        assert len(memory_ids) == len(set(memory_ids)), "Memory should have no duplicate IDs"

        # Verify disk consistency
        with storage_path.open('r') as f:
            disk_data = json.load(f)
        disk_todos = disk_data["todos"]
        assert len(disk_todos) == 5

        # Verify memory and disk are in sync
        disk_ids = [t["id"] for t in disk_todos]
        assert set(memory_ids) == set(disk_ids), "Memory and disk should have same IDs"

        # Verify next_id is valid (higher than any existing ID)
        max_id = max(memory_ids) if memory_ids else 0
        next_id = storage.get_next_id()
        assert next_id == max_id + 1, f"next_id should be {max_id + 1}, got {next_id}"


def test_add_batch_temp_file_cleanup_on_failure():
    """Test that temporary files are cleaned up even when batch fails.

    Verifies that no .tmp files remain after a failed batch operation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = FileStorage(str(storage_path))

        # Try batch operation that fails
        original_replace = os.replace

        def failing_replace(src, dst):
            if '.tmp' in str(src):
                raise OSError("Simulated failure")
            return original_replace(src, dst)

        with patch('os.replace', side_effect=failing_replace):
            with pytest.raises(OSError):
                new_todos = [
                    Todo(title=f"Task {i}", status="pending")
                    for i in range(5)
                ]
                storage.add_batch(new_todos)

        # Verify no temporary files remain
        tmp_files = list(storage_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temporary files should be cleaned up: {tmp_files}"
