"""Regression tests for issue #4735: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition (TOCTOU) between parent directory validation and mkdir in
_ensure_parent_directory function.

The function has multiple race windows:
1. Lines 35-40: Iterates through parents checking exists()/is_dir() - race window
2. Line 43: Second exists() check on parent before mkdir - another race window
3. Line 45: exist_ok=False combined with pre-validation can fail if race occurs

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_directory_creation_succeeds(tmp_path) -> None:
    """Issue #4735: Multiple threads saving to same new directory should succeed.

    Before fix: If two threads both check parent.exists() == False and then
    both try mkdir(exist_ok=False), one will fail with FileExistsError.

    After fix: Using exist_ok=True should handle this gracefully.
    """
    # Use a subdirectory that doesn't exist yet
    db = tmp_path / "newdir" / "subdir" / "todo.json"

    errors: list[Exception] = []
    successes: list[int] = []

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to the same new directory."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            successes.append(worker_id)
        except Exception as e:
            errors.append(e)

    # Create multiple threads that all try to create the same directory
    num_threads = 10
    threads = [threading.Thread(target=save_worker, args=(i,)) for i in range(num_threads)]

    # Start all threads simultaneously to maximize race condition chance
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join(timeout=10)

    # All threads should succeed (no FileExistsError from race condition)
    assert len(errors) == 0, f"Threads failed with errors: {errors}"
    assert len(successes) == num_threads, f"Expected {num_threads} successes, got {len(successes)}"

    # Verify the directory was created and file exists
    assert db.parent.exists(), "Parent directory should be created"
    assert db.exists(), "Database file should be created"


def test_concurrent_ensure_parent_directory_calls(tmp_path) -> None:
    """Issue #4735: Direct test of _ensure_parent_directory with concurrent calls.

    This tests the function directly without the overhead of TodoStorage.save().
    """
    # Use a subdirectory that doesn't exist yet
    file_path = tmp_path / "concurrent_dir" / "nested" / "file.txt"

    errors: list[Exception] = []

    def ensure_worker() -> None:
        try:
            _ensure_parent_directory(file_path)
        except Exception as e:
            errors.append(e)

    # Create multiple threads calling _ensure_parent_directory simultaneously
    num_threads = 20
    threads = [threading.Thread(target=ensure_worker) for _ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10)

    # All calls should succeed (no FileExistsError from race)
    assert len(errors) == 0, f"_ensure_parent_directory calls failed: {errors}"

    # Verify directory was created
    assert file_path.parent.exists(), "Parent directory should exist"


def test_file_as_directory_error_still_raised(tmp_path) -> None:
    """Issue #4735: File-as-directory validation must still work after fix.

    The fix should not remove the file-as-directory check. If a path component
    is a file (not directory), we must still raise a clear error.
    """
    # Create a file where a directory would need to exist
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file, not a directory")

    # Try to create a database path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should still raise ValueError for file-as-directory conflict
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        storage.save([Todo(id=1, text="test")])


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #4735: Normal nested directory creation should still work."""
    # Create a deeply nested path that doesn't exist
    db = tmp_path / "a" / "b" / "c" / "d" / "todo.json"
    storage = TodoStorage(str(db))

    # Should succeed
    storage.save([Todo(id=1, text="nested test")])

    # Verify file was created
    assert db.exists(), "Database file should be created"
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "nested test"


def test_existing_parent_directory_case(tmp_path) -> None:
    """Issue #4735: Should work when parent directory already exists."""
    # Pre-create the parent directory
    parent = tmp_path / "existing_dir"
    parent.mkdir()

    db = parent / "todo.json"
    storage = TodoStorage(str(db))

    # Should succeed without any issues
    storage.save([Todo(id=1, text="test")])

    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
