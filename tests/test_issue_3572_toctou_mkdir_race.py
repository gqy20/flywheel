"""Regression tests for issue #3572: TOCTOU race in _ensure_parent_directory.

Issue: The exists() check followed by mkdir(exist_ok=False) creates a race condition
where another process could create the directory between the check and the mkdir call,
causing FileExistsError.

These tests verify that concurrent saves to the same new directory path
complete successfully without FileExistsError.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_is_atomic_no_race(tmp_path) -> None:
    """Issue #3572: _ensure_parent_directory should not raise FileExistsError
    when directory is created by another process between check and mkdir.

    This test simulates the TOCTOU race condition by:
    1. Creating the parent directory right before _ensure_parent_directory runs
    2. Verifying no FileExistsError is raised
    """
    # Path to a file whose parent doesn't exist yet
    db_path = tmp_path / "newdir" / "subdir" / "db.json"
    parent_dir = db_path.parent

    # Verify parent doesn't exist
    assert not parent_dir.exists()

    # Simulate race: create parent directory just before calling ensure
    # This simulates what another process might do
    parent_dir.mkdir(parents=True)
    assert parent_dir.exists()

    # Now call _ensure_parent_directory - it should NOT raise FileExistsError
    # If it uses exist_ok=False after an exists() check, it will fail
    _ensure_parent_directory(db_path)

    # Parent should still exist
    assert parent_dir.exists()


def test_ensure_parent_directory_simulated_toctou_race(tmp_path) -> None:
    """Issue #3572: Simulate TOCTOU race by mocking exists() to return False while
    directory exists, triggering FileExistsError in vulnerable code.

    This test simulates a race condition where:
    1. exists() returns False (simulating point-in-time check)
    2. Another process creates the directory between exists() and mkdir()
    3. mkdir() with exist_ok=False would raise FileExistsError

    After the fix, this should complete without error.
    """
    db_path = tmp_path / "race_dir" / "db.json"
    parent_dir = db_path.parent

    # Pre-create the parent directory to simulate race condition
    # (another process creates it between exists() check and mkdir())
    parent_dir.mkdir(parents=True)

    original_exists = Path.exists

    def mock_exists(self):
        """Mock exists() that returns False for parent_dir even though it exists.

        This simulates the TOCTOU race: we checked, directory wasn't there,
        another process created it, now we try mkdir and fail.
        """
        # Always return False for parent_dir to force the vulnerable code path
        if self == parent_dir:
            return False
        return original_exists(self)

    with patch.object(Path, "exists", mock_exists):
        # With the vulnerable code (exist_ok=False after exists() check),
        # this would raise OSError because:
        # 1. exists() returned False
        # 2. Code tries mkdir(exist_ok=False)
        # 3. Directory actually exists -> FileExistsError (wrapped in OSError)
        #
        # With the fix (exist_ok=True or catching FileExistsError), this succeeds
        _ensure_parent_directory(db_path)

    # Directory should exist
    assert parent_dir.exists()


def test_concurrent_save_to_new_directory_no_file_exists_error(tmp_path) -> None:
    """Issue #3572: Concurrent save() calls to same new directory should not raise FileExistsError.

    This is a real-world test where multiple processes save to the same file
    whose parent directory doesn't exist yet.
    """
    db_path = tmp_path / "shared_new_dir" / "todos.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves to a file whose parent may be created by another process."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}-task")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug we're testing for - should NOT happen
            result_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Categorize results
    successes = [r for r in results if r[0] == "success"]
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # No FileExistsError should occur (this is the bug being fixed)
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race caused FileExistsError in workers: {file_exists_errors}"
    )

    # All workers should succeed
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. Errors: {other_errors}"
    )


def test_ensure_parent_directory_creates_when_missing(tmp_path) -> None:
    """Verify that _ensure_parent_directory still creates directories when missing."""
    # Path to file whose parent doesn't exist
    db_path = tmp_path / "level1" / "level2" / "level3" / "db.json"
    parent_dir = db_path.parent

    # Parent should not exist
    assert not parent_dir.exists()

    # Call ensure
    _ensure_parent_directory(db_path)

    # Now parent should exist
    assert parent_dir.exists()
    assert parent_dir.is_dir()


def test_ensure_parent_directory_handles_existing_directory(tmp_path) -> None:
    """Verify that _ensure_parent_directory handles existing directory gracefully."""
    # Create parent directory
    db_path = tmp_path / "existing_dir" / "db.json"
    db_path.parent.mkdir(parents=True)

    # Call ensure - should not raise
    _ensure_parent_directory(db_path)

    # Parent should still exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()
