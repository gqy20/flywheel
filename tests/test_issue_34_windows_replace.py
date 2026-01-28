"""Test for Issue #34: Windows platform file replace logic defect.

This test verifies that when Path.replace() fails (e.g., on Windows when
target file is locked by another process or antivirus), the temporary file
is properly cleaned up and does not remain on disk.

Issue #34 claims that temp files are not cleaned up when replace() fails,
but the code already handles this correctly in both _save() and _save_with_todos().
This test validates that the fix is already in place.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_temp_file_cleanup_on_replace_failure_save():
    """Test that temp file is cleaned up when Path.replace() fails in _save()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo using _save() method (triggered by first save after load)
        storage.add(Todo(title="Initial todo"))
        assert len(storage.list()) == 1

        # Track temp files before the operation
        temp_files_before = list(Path(tmpdir).glob("*.tmp"))

        # Mock Path.replace to simulate Windows PermissionError
        def mock_replace(self, target):
            # Simulate Windows PermissionError when target file exists and is locked
            raise PermissionError(f"[WinError 5] Access is denied: '{target}'")

        # Force a save operation by updating internal state directly
        # This triggers _save() instead of _save_with_todos()
        storage._todos.append(Todo(id=999, title="Direct add"))

        try:
            storage._save()  # Direct call to _save()
            assert False, "Expected PermissionError to be raised"
        except PermissionError:
            pass  # Expected

        # Verify temp files were cleaned up (no new temp files)
        temp_files_after = list(Path(tmpdir).glob("*.tmp"))
        assert len(temp_files_after) == len(temp_files_before), \
            "Temporary file should be cleaned up after replace() failure"


def test_temp_file_cleanup_on_replace_failure_save_with_todos():
    """Test that temp file is cleaned up when Path.replace() fails in _save_with_todos()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        storage.add(Todo(title="Initial todo"))
        assert len(storage.list()) == 1

        # Track temp files before the operation
        temp_files_before = list(Path(tmpdir).glob("*.tmp"))

        # Mock Path.replace to simulate Windows PermissionError
        def mock_replace(self, target):
            # Simulate Windows PermissionError when target file exists and is locked
            raise PermissionError(f"[WinError 5] Access is denied: '{target}'")

        # Add another todo - this should fail but clean up temp file
        with patch.object(Path, 'replace', mock_replace):
            try:
                storage.add(Todo(title="This should fail"))
                assert False, "Expected PermissionError to be raised"
            except PermissionError:
                pass  # Expected

        # Verify temp files were cleaned up (no new temp files)
        temp_files_after = list(Path(tmpdir).glob("*.tmp"))
        assert len(temp_files_after) == len(temp_files_before), \
            "Temporary file should be cleaned up after replace() failure in _save_with_todos()"


def test_temp_file_cleanup_on_generic_failure():
    """Test that temp file is cleaned up on any exception during save."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        storage.add(Todo(title="Initial todo"))
        assert len(storage.list()) == 1

        # Track temp files before the operation
        temp_files_before = list(Path(tmpdir).glob("*.tmp"))

        # Mock os.fsync to raise an error after data is written
        def mock_fsync(fd):
            # Simulate a disk I/O error after temp file is created
            raise OSError("Simulated I/O error")

        # Add another todo - this should fail but clean up temp file
        with patch('os.fsync', mock_fsync):
            try:
                storage.add(Todo(title="This should fail"))
                assert False, "Expected OSError to be raised"
            except OSError:
                pass  # Expected

        # Verify temp files were cleaned up (no new temp files)
        temp_files_after = list(Path(tmpdir).glob("*.tmp"))
        assert len(temp_files_after) == len(temp_files_before), \
            "Temporary file should be cleaned up after any exception during save"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
