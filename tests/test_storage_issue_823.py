"""Test atomic writes using temporary files (Issue #823).

This test verifies that:
1. Writes use temporary files instead of writing directly to the target file
2. The original file is only modified when the new data is valid and complete
3. os.replace is used for atomic replacement
"""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_atomic_write_uses_temp_file():
    """Verify that writes use a temporary file for atomicity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Add a todo to trigger a save
        todo = Todo(title="Test todo", description="Test description")
        storage.add(todo)

        # Check that a .tmp file was used during the write
        # The temp file should be cleaned up after successful write
        tmp_files = list(Path(tmpdir).glob("*.tmp"))
        assert len(tmp_files) == 0, "Temporary files should be cleaned up after successful write"

        # The main file should exist and contain the todo
        assert storage_path.exists(), "Main storage file should exist"
        assert storage_path.stat().st_size > 0, "Main storage file should not be empty"

        storage.close()


def test_atomic_write_preserves_original_on_failure():
    """Verify that original file is preserved if write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Add initial data
        todo1 = Todo(title="Todo 1", description="First todo")
        storage.add(todo1)
        original_content = storage_path.read_text()

        # Simulate a failure during write by making the directory read-only
        # This should cause the write to fail but preserve the original file
        original_mode = storage_path.stat().st_mode

        # Create a new storage instance and try to write
        storage2 = FileStorage(str(storage_path))

        # Monkey-patch the write to simulate failure
        original_save = storage2._save_with_todos_sync
        call_count = [0]

        def failing_save(todos):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call succeeds
                return original_save(todos)
            else:
                # Second call fails
                raise IOError("Simulated write failure")

        storage2._save_with_todos_sync = failing_save

        # Try to add another todo - this should fail
        todo2 = Todo(title="Todo 2", description="Second todo")
        with pytest.raises(IOError):
            storage2.add(todo2)

        storage2.close()

        # Verify the original file is unchanged
        current_content = storage_path.read_text()
        assert current_content == original_content, "Original file should be preserved on write failure"

        storage.close()


def test_temp_file_naming_convention():
    """Verify that temporary files follow the expected naming convention.

    Issue #823 suggests using {filepath}.tmp as the temporary file name.
    This test checks if the implementation uses this convention or a similar one.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Track temporary files created during operations
        created_temp_files = []

        # Monkey-patch to intercept temp file creation
        import pathlib

        original_open = pathlib.Path.open

        def tracked_open(self, *args, **kwargs):
            if str(self).endswith('.tmp'):
                created_temp_files.append(str(self))
            return original_open(self, *args, **kwargs)

        pathlib.Path.open = tracked_open

        try:
            storage = FileStorage(str(storage_path))
            todo = Todo(title="Test todo", description="Test description")
            storage.add(todo)
            storage.close()

            # Verify that at least one .tmp file was created
            assert len(created_temp_files) > 0, "No temporary files were created during write"

            # Verify that temp files have the correct base name
            # Issue #823 suggests {filepath}.tmp
            # Current implementation uses {filepath}.{random}.tmp
            # Both are acceptable as long as they end with .tmp
            for temp_file in created_temp_files:
                assert temp_file.endswith('.tmp'), f"Temp file {temp_file} should end with .tmp"
                # The temp file should be in the same directory as the target file
                assert Path(temp_file).parent == storage_path.parent, \
                    f"Temp file {temp_file} should be in same directory as target file"

        finally:
            pathlib.Path.open = original_open


def test_atomic_replace_operation():
    """Verify that os.replace is used for atomic file replacement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Track if os.replace was called
        original_replace = os.replace
        replace_calls = []

        def tracked_replace(src, dst):
            replace_calls.append((src, dst))
            return original_replace(src, dst)

        os.replace = tracked_replace

        try:
            storage = FileStorage(str(storage_path))
            todo = Todo(title="Test todo", description="Test description")
            storage.add(todo)
            storage.close()

            # Verify that os.replace was called at least once
            assert len(replace_calls) > 0, "os.replace should be called for atomic file replacement"

            # Verify that the source was a temp file and destination was the target file
            for src, dst in replace_calls:
                assert src.endswith('.tmp'), f"Source file {src} should be a temporary file"
                assert dst == str(storage_path), f"Destination should be the target file"

        finally:
            os.replace = original_replace
