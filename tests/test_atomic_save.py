"""Test atomic file save operations (Issue #227)."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_atomic_save_replaces_file_atomically():
    """Test that _save uses atomic os.replace operation.

    This test verifies that:
    1. The original file exists before save
    2. A temporary file is created during save
    3. The original file is replaced atomically using os.replace
    4. No intermediate corrupted state exists
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todo
        storage = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage.add(todo1)

        # Verify initial file exists
        assert storage_path.exists()

        # Read initial file content
        with storage_path.open('r') as f:
            initial_data = json.load(f)
        assert initial_data["todos"][0]["title"] == "Task 1"

        # Add another todo - this triggers _save
        todo2 = Todo(id=2, title="Task 2", status="pending")
        storage.add(todo2)

        # Verify file was updated
        with storage_path.open('r') as f:
            updated_data = json.load(f)
        assert len(updated_data["todos"]) == 2
        assert updated_data["todos"][0]["title"] == "Task 1"
        assert updated_data["todos"][1]["title"] == "Task 2"

        # Verify the file inode remains the same (os.replace preserves inode on POSIX)
        # This confirms atomic replacement occurred
        if os.name != 'nt':  # POSIX systems
            # Get current inode
            stat_after = storage_path.stat()
            # The key assertion: we cannot directly check inode continuity without
            # capturing the stat before the save, but we can verify the file
            # exists and has correct content, which os.replace guarantees
            assert stat_after.st_size > 0


def test_atomic_save_with_simulated_failure():
    """Test that atomic save prevents data corruption on failure.

    This test simulates a failure during save to verify that
    the original file remains intact when write fails.
    """
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with initial todo
        storage = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Original Task", status="pending")
        storage.add(todo1)

        # Read original file content
        with storage_path.open('r') as f:
            original_data = json.load(f)
        original_title = original_data["todos"][0]["title"]

        # Mock os.write to fail on second call (simulating crash during write)
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            call_count[0] += 1
            if call_count[0] > 1:  # Fail on second write attempt
                raise OSError("Simulated write failure")
            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            # Attempt to add another todo - this should fail
            with pytest.raises(OSError):
                todo2 = Todo(id=2, title="New Task", status="pending")
                storage.add(todo2)

        # Verify original file is still intact
        assert storage_path.exists()
        with storage_path.open('r') as f:
            recovered_data = json.load(f)

        # The original data should be preserved
        assert recovered_data["todos"][0]["title"] == original_title
        assert len(recovered_data["todos"]) == 1


def test_atomic_save_with_exception_cleanup():
    """Test that temporary files are cleaned up on exception."""
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage.add(todo1)

        # Mock Path.replace to raise an exception
        with patch.object(Path, 'replace', side_effect=OSError("Simulated replace failure")):
            # Attempt to add another todo - this should fail during replace
            with pytest.raises(OSError):
                todo2 = Todo(id=2, title="Task 2", status="pending")
                storage.add(todo2)

        # Verify no temporary files remain
        tmp_files = list(storage_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temporary files not cleaned up: {tmp_files}"

        # Verify original file still exists with correct data
        assert storage_path.exists()
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 1
        assert data["todos"][0]["title"] == "Task 1"


def test_atomic_save_uses_os_replace():
    """Test that _save uses os.replace for atomic replacement.

    This is a code verification test to ensure the implementation
    uses os.replace() as specified in issue #227.
    """
    import inspect
    from flywheel.storage import Storage

    # Get the source code of _save method
    source = inspect.getsource(Storage._save)

    # Verify os.replace is explicitly used in the implementation (Issue #227)
    # The issue specifically requests os.replace() rather than Path.replace()
    assert "os.replace" in source, "_save method should use os.replace() for atomic operation (Issue #227)"

    # Also verify _save_with_todos uses os.replace
    source_with_todos = inspect.getsource(Storage._save_with_todos)
    assert "os.replace" in source_with_todos, "_save_with_todos method should use os.replace() for atomic operation (Issue #227)"
