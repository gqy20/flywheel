"""Regression tests for issue #4508: TOCTOU race condition in _ensure_parent_directory.

Issue: TOCTOU race condition in _ensure_parent_directory: file type check exists()
followed by is_dir() with mkdir() allows race window.

The vulnerability exists because:
1. part.exists() and part.is_dir() are separate system calls, creating a race window
2. parent.exists() followed by mkdir() - another process could create between check and mkdir

Fix: Replace the exists/is_dir/mkdir pattern with a single atomic mkdir(parents=True, exist_ok=True)
and catch FileExistsError to provide better error message.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_parent_creation_concurrent(tmp_path) -> None:
    """Issue #4508: Test concurrent directory creation doesn't fail due to TOCTOU race.

    Before fix: If another process creates the parent directory between the
    exists() check and the mkdir() call, mkdir() would fail with FileExistsError.

    After fix: Using mkdir(parents=True, exist_ok=True) handles this atomically.
    """
    db_path = tmp_path / "level1" / "level2" / "todo.json"

    errors = multiprocessing.Manager().list()
    start_barrier = multiprocessing.Barrier(5)  # Synchronize all workers to start at same time

    def worker(worker_id: int) -> None:
        try:
            # Wait for all workers to be ready
            start_barrier.wait(timeout=5)
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Run multiple processes trying to create the same parent directory concurrently
    processes = []
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=10)

    # With atomic mkdir, no errors should occur
    assert len(errors) == 0, f"Workers encountered TOCTOU race errors: {list(errors)}"


def test_toctou_race_file_as_directory_still_detected(tmp_path) -> None:
    """Issue #4508: After fix, file-as-directory conflict should still be detected.

    The fix should maintain the security property that we detect when a path
    component exists as a file (not a directory) and fail with a clear error.
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create db that requires blocking_file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # This should still fail with ValueError about file vs directory
    with pytest.raises(ValueError, match=r"(file|directory|path)"):
        _ensure_parent_directory(Path(db_path))


def test_toctou_mkdir_with_exist_ok_handles_concurrent_creation(tmp_path) -> None:
    """Issue #4508: Verify mkdir with exist_ok=True handles concurrent creation.

    This test verifies the fix by checking that a second call to _ensure_parent_directory
    for the same path doesn't fail even if the directory was created by another process.
    """
    db_path = tmp_path / "concurrent" / "test.json"

    # First call - creates directory
    _ensure_parent_directory(Path(db_path))
    assert db_path.parent.exists()

    # Second call - should not fail even though directory already exists
    # (simulates race condition where directory was created between check and mkdir)
    _ensure_parent_directory(Path(db_path))  # Should not raise


def test_ensure_parent_directory_atomic_error_message(tmp_path) -> None:
    """Issue #4508: Verify that FileExistsError (file vs directory) provides clear message.

    When a path component exists as a file instead of directory, the error message
    should still be clear and helpful after the fix.
    """
    # Create nested file structure that blocks directory creation
    blocking_file = tmp_path / "existing_file.txt"
    blocking_file.write_text("content")

    # Path that requires blocking_file to be a directory
    db_path = blocking_file / "deep" / "nested" / "todo.json"

    # Should raise ValueError with helpful message
    with pytest.raises(ValueError) as exc_info:
        _ensure_parent_directory(Path(db_path))

    error_msg = str(exc_info.value).lower()
    # Error message should indicate the problem
    assert "file" in error_msg or "not a directory" in error_msg or "path" in error_msg


def test_ensure_parent_directory_success_with_nested_path(tmp_path) -> None:
    """Issue #4508: Verify normal nested directory creation still works after fix."""
    db_path = tmp_path / "deeply" / "nested" / "path" / "todo.json"

    # Should succeed without raising
    _ensure_parent_directory(Path(db_path))

    # Directory should be created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_storage_save_after_race_fix_still_atomic(tmp_path) -> None:
    """Issue #4508: Verify that storage save operations work correctly after race fix."""
    db_path = tmp_path / "new" / "dir" / "db.json"
    storage = TodoStorage(str(db_path))

    # Should successfully create parent and save
    todos = [Todo(id=1, text="test after fix")]
    storage.save(todos)

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test after fix"
