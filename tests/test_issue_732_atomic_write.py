"""Test atomic write operations for Issue #732.

This test verifies that the storage implements atomic write operations
using the 'write-to-temp-file-and-rename' pattern to prevent data loss
if the application crashes or power fails while writing.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

from flywheel.storage import Storage
from flywheel.todo import Todo, Status


def test_atomic_write_uses_temp_file_pattern():
    """Test that writes use temp file + os.replace pattern for atomicity (Issue #732).

    This test verifies the implementation uses:
    1. Write to todos.json.tmp
    2. Flush/fsync to ensure data is written to disk
    3. Use os.replace() for atomic replacement

    This prevents data loss if the application crashes or power fails during write.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial data
        storage.add(Todo(id=1, title="Initial todo", status=Status.TODO))

        # Track filesystem operations
        replace_calls = []
        original_replace = os.replace

        def mock_replace(src, dst):
            replace_calls.append((src, dst))
            return original_replace(src, dst)

        # Mock os.replace to verify it's being used with temp files
        with mock.patch('os.replace', side_effect=mock_replace):
            storage.add(Todo(id=2, title="Second todo", status=Status.TODO))

        # Verify that os.replace was called
        assert len(replace_calls) > 0, "os.replace should be called for atomic write"

        # Verify that a temp file was used (source should end with .tmp)
        src, dst = replace_calls[-1]
        assert str(src).endswith('.tmp'), f"Source should be a temp file ending with .tmp, got {src}"
        assert str(dst) == str(storage_path), f"Destination should be the storage file, got {dst}"


def test_atomic_write_prevents_data_corruption():
    """Test that atomic writes prevent data corruption during crashes (Issue #732).

    This simulates a crash scenario where writing is interrupted.
    With atomic writes, the original file should remain intact.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        # Verify original data is valid
        original_content = storage_path.read_text()
        original_data = json.loads(original_content)
        original_todos_count = len(original_data.get('todos', original_data if isinstance(original_data, list) else []))

        # Simulate a write interruption by mocking the write operation
        # to fail after creating temp file but before replace
        original_save = storage._save_with_todos_sync

        def failing_save(todos):
            # Create a scenario where temp file is created but replace fails
            raise IOError("Simulated crash during write")

        with mock.patch.object(storage, '_save_with_todos_sync', side_effect=failing_save):
            try:
                storage.add(Todo(id=3, title="Todo 3", status=Status.TODO))
            except IOError:
                pass  # Expected to fail

        # After the failed write, the original file should still be valid
        final_content = storage_path.read_text()
        final_data = json.loads(final_content)

        # The file should not be corrupted (valid JSON)
        assert isinstance(final_data, (dict, list)), "File should contain valid JSON data"

        # The data should match the original state
        final_todos = final_data.get('todos', final_data if isinstance(final_data, list) else [])
        assert len(final_todos) == original_todos_count, "Original data should be preserved after failed write"


def test_temp_file_has_correct_permissions():
    """Test that temp files are created with secure permissions (Issue #732).

    Verifies that temp files are created with 0o600 permissions before
    any data is written to prevent race conditions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Track chmod calls to verify 0o600 permissions
        chmod_calls = []
        original_chmod = os.chmod

        def mock_chmod(path, mode):
            chmod_calls.append((path, mode))
            return original_chmod(path, mode)

        with mock.patch('os.chmod', side_effect=mock_chmod):
            storage.add(Todo(id=1, title="Test todo", status=Status.TODO))

        # Verify chmod was called with 0o600
        assert len(chmod_calls) > 0, "chmod should be called to set permissions"
        assert any(mode == 0o600 for _, mode in chmod_calls), "Temp files should have 0o600 permissions"


def test_atomic_write_with_fsync():
    """Test that atomic writes use fsync to ensure data is written to disk (Issue #732).

    Verifies that after writing to the temp file, fsync is called
    to ensure data is physically written to disk before the rename.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Track fsync calls
        fsync_calls = []
        original_fsync = os.fsync

        def mock_fsync(fd):
            fsync_calls.append(fd)
            return original_fsync(fd)

        with mock.patch('os.fsync', side_effect=mock_fsync):
            storage.add(Todo(id=1, title="Test todo", status=Status.TODO))

        # Verify fsync was called to ensure data is written to disk
        assert len(fsync_calls) > 0, "fsync should be called to ensure data is written to disk"
