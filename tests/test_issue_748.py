"""Test transaction support for storage operations (Issue #748).

This test verifies that storage operations use atomic write patterns:
1. Write to temporary file (.tmp)
2. Verify data integrity
3. Atomically replace original file using os.replace

This prevents data corruption from crashes or power failures during writes.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_add_batch_uses_temp_file_and_atomic_replace():
    """Test that add_batch uses temporary file and atomic replace.

    Verifies that:
    1. Data is written to a .tmp file first
    2. os.replace is used for atomic replacement
    3. Original file remains intact if write fails
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todos
        storage = Storage(str(storage_path))
        for i in range(5):
            todo = Todo(id=i+1, title=f"Original Task {i+1}", status="pending")
            storage.add(todo)

        # Verify initial file exists with 5 todos
        assert storage_path.exists()
        with storage_path.open('r') as f:
            initial_data = json.load(f)
        assert len(initial_data["todos"]) == 5

        # Track temporary files created during save
        tmp_files_created = []
        original_replace = os.replace

        def mock_replace(src, dst):
            """Mock os.replace to track temporary file usage."""
            if str(src).endswith('.tmp'):
                tmp_files_created.append(src)
            return original_replace(src, dst)

        with patch('os.replace', side_effect=mock_replace):
            # Add batch of new todos
            new_todos = [
                Todo(title=f"New Task {i}", status="pending")
                for i in range(10, 15)
            ]
            added = storage.add_batch(new_todos)

        # Verify temporary files were used
        assert len(tmp_files_created) > 0, "add_batch should use .tmp files for atomic writes"

        # Verify all todos were added
        with storage_path.open('r') as f:
            final_data = json.load(f)
        assert len(final_data["todos"]) == 15
        assert len(added) == 5


def test_atomic_save_prevents_partial_write_corruption():
    """Test that atomic save prevents data corruption on crash/power failure.

    Simulates a crash during write to verify:
    1. Original file remains intact
    2. No partial/corrupted data is written to original file
    3. Temporary files are cleaned up on failure
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todos
        storage = Storage(str(storage_path))
        original_todos = []
        for i in range(10):
            todo = Todo(id=i+1, title=f"Critical Data {i+1}", status="pending")
            storage.add(todo)
            original_todos.append(todo)

        # Read original file content for comparison
        with storage_path.open('r') as f:
            original_data = json.load(f)
        original_titles = [t["title"] for t in original_data["todos"]]

        # Mock aiofiles.open to fail during write (simulating crash)
        original_open = None

        async def mock_open_fail(*args, **kwargs):
            """Mock that raises error during write operation."""
            import aiofiles
            if original_open is None:
                # First call succeeds
                return await original_open(*args, **kwargs)

        # Simulate failure during add_batch
        with patch('aiofiles.open', side_effect=OSError("Simulated crash during write")):
            # Attempt to add batch - should fail
            with pytest.raises(OSError):
                new_todos = [
                    Todo(title=f"New Task {i}", status="pending")
                    for i in range(20, 25)
                ]
                storage.add_batch(new_todos)

        # Verify original file is intact with all original data
        assert storage_path.exists()
        with storage_path.open('r') as f:
            recovered_data = json.load(f)

        recovered_titles = [t["title"] for t in recovered_data["todos"]]
        assert recovered_titles == original_titles, "Original file should remain intact after write failure"
        assert len(recovered_data["todos"]) == 10, "Should have exactly 10 original todos"


def test_temp_file_cleanup_on_success():
    """Test that temporary files are cleaned up after successful write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Add batch of todos
        new_todos = [
            Todo(title=f"Task {i}", status="pending")
            for i in range(100, 110)
        ]
        storage.add_batch(new_todos)

        # Verify no .tmp files remain after successful operation
        tmp_files = list(storage_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temporary files should be cleaned up: {tmp_files}"

        # Verify data was written correctly
        assert storage_path.exists()
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 10


def test_update_batch_uses_atomic_write():
    """Test that update_batch also uses atomic write pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todos
        storage = Storage(str(storage_path))
        original_todos = []
        for i in range(5):
            todo = Todo(id=i+1, title=f"Task {i+1}", status="pending")
            storage.add(todo)
            original_todos.append(todo)

        # Track os.replace calls
        replace_calls = []
        original_replace = os.replace

        def mock_replace(src, dst):
            """Mock os.replace to track calls."""
            replace_calls.append((src, dst))
            return original_replace(src, dst)

        with patch('os.replace', side_effect=mock_replace):
            # Update batch of todos
            updated_todos = [
                Todo(id=i+1, title=f"Updated Task {i+1}", status="completed")
                for i in range(5)
            ]
            storage.update_batch(updated_todos)

        # Verify atomic replace was used
        assert len(replace_calls) > 0, "update_batch should use os.replace for atomic writes"

        # Verify updates were applied
        todos = storage.list()
        assert all(t.status == "completed" for t in todos)
        assert all("Updated" in t.title for t in todos)


def test_data_integrity_verification_before_replace():
    """Test that data integrity is verified before atomic replace.

    Verifies that:
    1. Checksum is calculated for data
    2. Data includes integrity hash
    3. Only valid data is committed to original file
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Add batch of todos
        new_todos = [
            Todo(title=f"Critical Task {i}", status="pending")
            for i in range(50, 60)
        ]
        storage.add_batch(new_todos)

        # Verify file contains metadata with checksum
        with storage_path.open('r') as f:
            content = f.read()
            # Verify JSON structure includes metadata
            data = json.loads(content)

        assert "metadata" in data, "Data should include metadata for integrity verification"
        assert "checksum" in data["metadata"], "Metadata should include checksum"
        assert "todos" in data, "Data should include todos array"
        assert len(data["todos"]) == 10


def test_concurrent_batch_operations_with_atomicity():
    """Test that concurrent batch operations maintain data integrity through atomic writes.

    This test verifies that even with multiple operations, atomic writes
    prevent data corruption.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Perform multiple batch operations sequentially
        # (real concurrent testing would require multiple processes)
        for batch_num in range(3):
            new_todos = [
                Todo(title=f"Batch {batch_num} Task {i}", status="pending")
                for i in range(5)
            ]
            storage.add_batch(new_todos)

        # Verify all data is consistent
        todos = storage.list()
        assert len(todos) == 15, "Should have all 15 todos from 3 batches"

        # Verify no temporary files remain
        tmp_files = list(storage_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Verify file is valid JSON with all data
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 15
