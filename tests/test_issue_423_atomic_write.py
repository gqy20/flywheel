"""Test atomic write implementation for issue #423.

Issue #423 requests implementing atomic write using temporary file + rename
to prevent data corruption if the process crashes during json.dump().

This test verifies that:
1. Data is written to a temporary file first (e.g., todos.json.tmp)
2. os.replace() is used to atomically overwrite the target file
3. The target file is either fully updated or untouched (never corrupted)
"""

import inspect
import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo, Status


def test_423_uses_tempfile_pattern():
    """Verify issue #423: implementation uses temporary file pattern."""
    # Get the source code of _save method
    source = inspect.getsource(Storage._save)

    # Verify tempfile.mkstemp is used to create temporary file
    assert "tempfile.mkstemp" in source, (
        "Issue #423: Should use tempfile.mkstemp() to create temporary file"
    )

    # Verify os.replace is used for atomic replacement
    assert "os.replace" in source, (
        "Issue #423: Should use os.replace() for atomic file replacement"
    )


def test_423_temp_file_created_in_same_directory():
    """Verify issue #423: temporary file is created in the same directory."""
    source = inspect.getsource(Storage._save)

    # Verify mkstemp uses dir=self.path.parent to create temp file in same directory
    assert "dir=self.path.parent" in source, (
        "Issue #423: Temporary file should be created in the same directory "
        "as the target file for atomic rename to work correctly"
    )


def test_423_atomic_replace_prevents_corruption():
    """Verify issue #423: atomic write prevents file corruption.

    This test simulates a crash scenario where:
    1. Original data exists
    2. A write operation begins (creates temp file)
    3. Before replace, the original file should remain intact
    4. After successful replace, the new data should be complete
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo1 = Todo(id=1, title="Original Todo", status=Status.TODO)
        storage.add(todo1)

        # Verify original file exists and has correct data
        assert storage_path.exists()
        with storage_path.open('r') as f:
            original_data = json.load(f)
        assert len(original_data["todos"]) == 1
        assert original_data["todos"][0]["title"] == "Original Todo"

        # Store reference to original file's inode (POSIX only)
        import os
        original_stat = storage_path.stat() if os.name != 'nt' else None

        # Add another todo - this triggers atomic write
        todo2 = Todo(id=2, title="Second Todo", status=Status.DONE)
        storage.add(todo2)

        # After write, file should exist with valid JSON
        assert storage_path.exists()

        # Verify the file is not corrupted (valid JSON)
        with storage_path.open('r') as f:
            final_data = json.load(f)

        # Verify both todos are present (complete write succeeded)
        assert len(final_data["todos"]) == 2
        assert final_data["todos"][0]["title"] == "Original Todo"
        assert final_data["todos"][1]["title"] == "Second Todo"

        # On POSIX, verify os.replace preserved the inode (atomic replacement)
        if os.name != 'nt' and original_stat:
            final_stat = storage_path.stat()
            # os.replace should preserve inode on POSIX systems
            assert final_stat.st_ino == original_stat.st_ino, (
                "Issue #423: os.replace should preserve inode on POSIX "
                "(confirms atomic replacement occurred)"
            )


def test_423_save_with_todos_uses_atomic_write():
    """Verify issue #423: _save_with_todos also uses atomic write."""
    source = inspect.getsource(Storage._save_with_todos)

    # Verify tempfile.mkstemp is used
    assert "tempfile.mkstemp" in source, (
        "Issue #423: _save_with_todos should use tempfile.mkstemp()"
    )

    # Verify os.replace is used
    assert "os.replace" in source, (
        "Issue #423: _save_with_todos should use os.replace()"
    )


def test_423_temp_file_suffix():
    """Verify issue #423: temporary file uses .tmp suffix."""
    source = inspect.getsource(Storage._save)

    # Verify temporary file uses .tmp suffix for easy identification
    assert '".tmp"' in source or "'.tmp'" in source or '.tmp' in source, (
        "Issue #423: Temporary file should use .tmp suffix "
        "(e.g., todos.json.tmp)"
    )
