"""Regression tests for issue #3620: TOCTOU race condition in _ensure_parent_directory.

Issue: TOCTOU race condition between checking if parent exists and calling mkdir()
with exist_ok=False. Another process could create the directory between the check
and mkdir, causing an OSError (FileExistsError) even though the operation should succeed.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_concurrent_directory_creation(tmp_path) -> None:
    """Issue #3620: Should not raise OSError when another process creates the directory.

    Before fix: exist_ok=False causes OSError/FileExistsError if another process
                creates the directory between the check and mkdir.
    After fix: exist_ok=True handles the race condition gracefully.
    """
    # Create a unique nested path that doesn't exist yet
    nested_path = tmp_path / "level1" / "level2" / "level3" / "todo.json"

    # Track mkdir calls to simulate the race condition
    mkdir_call_count = 0
    original_mkdir = Path.mkdir

    def race_simulating_mkdir(self, *args, **kwargs):
        nonlocal mkdir_call_count
        mkdir_call_count += 1

        # On the first mkdir call, simulate another process creating the directory
        # right before our mkdir executes
        if mkdir_call_count == 1 and not self.exists():
            # Simulate another process creating this directory
            original_mkdir(self, parents=True, exist_ok=True)

        # Now call the original mkdir with the passed exist_ok value
        # Before fix: this would fail because exist_ok=False but dir now exists
        # After fix: this succeeds because exist_ok=True
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", race_simulating_mkdir):
        # This should NOT raise an OSError after the fix
        _ensure_parent_directory(nested_path)

    # Verify directory was created
    assert nested_path.parent.exists()
    assert nested_path.parent.is_dir()


def test_concurrent_ensure_parent_directory_calls(tmp_path) -> None:
    """Issue #3620: Multiple concurrent calls to _ensure_parent_directory should all succeed.

    Uses multiprocessing to simulate true concurrent directory creation.
    """
    shared_path = tmp_path / "shared" / "nested" / "todo.json"
    success_count = multiprocessing.Value("i", 0)
    error_count = multiprocessing.Value("i", 0)

    def ensure_dir_worker(worker_id: int) -> None:
        """Worker that calls _ensure_parent_directory on the same path."""
        try:
            # Small stagger to increase race likelihood
            time.sleep(0.001 * worker_id)
            _ensure_parent_directory(shared_path)
            with success_count.get_lock():
                success_count.value += 1
        except (OSError, FileExistsError):
            # Before fix: This would be hit due to TOCTOU race
            with error_count.get_lock():
                error_count.value += 1

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=ensure_dir_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # All workers should succeed (no TOCTOU errors)
    assert error_count.value == 0, (
        f"TOCTOU race condition detected: {error_count.value} workers failed. "
        f"This indicates mkdir is using exist_ok=False which causes FileExistsError."
    )
    assert success_count.value == num_workers

    # Directory should exist
    assert shared_path.parent.exists()


def test_storage_save_with_concurrent_directory_creation(tmp_path) -> None:
    """Issue #3620: TodoStorage.save() should succeed when another process creates parent dir.

    Simulates the race condition in the context of TodoStorage.save() operation.
    """
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"

    mkdir_call_count = 0
    original_mkdir = Path.mkdir

    def race_simulating_mkdir(self, *args, **kwargs):
        nonlocal mkdir_call_count
        mkdir_call_count += 1

        # Simulate TOCTOU: another process creates the directory after our check
        # but before our mkdir
        if mkdir_call_count == 1 and not self.exists():
            original_mkdir(self, parents=True, exist_ok=True)

        return original_mkdir(self, *args, **kwargs)

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="test todo")]

    with patch.object(Path, "mkdir", race_simulating_mkdir):
        # Before fix: This raises OSError due to exist_ok=False
        # After fix: This succeeds
        storage.save(todos)

    # Verify the todo was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_file_as_directory_validation_still_works(tmp_path) -> None:
    """Issue #3620: The fix should not break file-as-directory validation.

    Even with exist_ok=True, we should still get a clear error when
    a parent path component is a file.
    """
    # Create a file where a directory would be needed
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create a path that requires the file to be a directory
    invalid_path = blocking_file / "subdir" / "todo.json"

    # Should raise ValueError, not OSError
    with pytest.raises(ValueError, match=r"(not a directory|exists as a file)"):
        _ensure_parent_directory(invalid_path)


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #3620: Normal nested directory creation should still work after fix."""
    nested_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

    _ensure_parent_directory(nested_path)

    # All directories should be created
    assert nested_path.parent.exists()
    assert nested_path.parent.is_dir()


def test_existing_directory_is_handled_gracefully(tmp_path) -> None:
    """Issue #3620: When directory already exists, no error should be raised."""
    # Pre-create the directory
    parent_dir = tmp_path / "existing" / "dir"
    parent_dir.mkdir(parents=True)

    file_path = parent_dir / "todo.json"

    # Should succeed without any error
    _ensure_parent_directory(file_path)

    assert parent_dir.exists()
