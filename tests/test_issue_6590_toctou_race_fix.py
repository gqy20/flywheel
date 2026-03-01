"""Regression tests for issue #6590: TOCTOU race condition in _ensure_parent_directory.

Issue: In _ensure_parent_directory, exist_ok=False combined with the preceding
parent.exists() check creates a TOCTOU (Time-of-Check-Time-of-Use) race condition.
Between checking if the parent exists and calling mkdir, another process may
have already created the directory, causing FileExistsError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_concurrent_directory_creation(tmp_path) -> None:
    """Issue #6590: Concurrent processes creating same parent directory should not fail.

    Before fix: exist_ok=False causes FileExistsError when multiple processes
    try to create the same parent directory concurrently.
    After fix: exist_ok=True handles the race condition gracefully.
    """
    # Use a path that requires creating a new parent directory
    db_path = tmp_path / "new_subdir" / "todo.json"

    errors_queue: multiprocessing.Queue = multiprocessing.Queue()
    success_count = multiprocessing.Value("i", 0)

    def ensure_dir_worker(worker_id: int) -> None:
        """Worker that tries to ensure parent directory exists."""
        try:
            # Small delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            _ensure_parent_directory(db_path)
            with success_count.get_lock():
                success_count.value += 1
        except FileExistsError as e:
            errors_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            errors_queue.put((type(e).__name__, worker_id, str(e)))

    # Run multiple workers that all try to create the same directory
    num_workers = 10
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=ensure_dir_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect errors
    errors = []
    while not errors_queue.empty():
        errors.append(errors_queue.get())

    # No worker should encounter FileExistsError (the TOCTOU race symptom)
    file_exists_errors = [e for e in errors if e[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race caused FileExistsError in {len(file_exists_errors)} workers: "
        f"{file_exists_errors}"
    )

    # All workers should succeed
    assert success_count.value == num_workers, (
        f"Expected {num_workers} successes, got {success_count.value}. "
        f"Errors: {errors}"
    )

    # Directory should exist after all workers complete
    assert db_path.parent.exists(), "Parent directory should exist after concurrent creation"


def test_toctou_race_concurrent_save_to_new_path(tmp_path) -> None:
    """Issue #6590: Concurrent saves to a new path should not fail with FileExistsError.

    This simulates the real-world scenario where multiple processes try to save
    to the same database path that requires parent directory creation.
    """
    # Use a path that requires creating new parent directories
    db_path = tmp_path / "deeply" / "nested" / "new_dir" / "todo.json"

    errors_queue: multiprocessing.Queue = multiprocessing.Queue()
    success_count = multiprocessing.Value("i", 0)

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to the same new path."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}-todo")]
            storage.save(todos)
            with success_count.get_lock():
                success_count.value += 1
        except FileExistsError as e:
            errors_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            errors_queue.put((type(e).__name__, worker_id, str(e)))

    # Run multiple workers that all try to save to the same new path
    num_workers = 8
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect errors
    errors = []
    while not errors_queue.empty():
        errors.append(errors_queue.get())

    # No worker should encounter FileExistsError (the TOCTOU race symptom)
    file_exists_errors = [e for e in errors if e[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race caused FileExistsError during save in {len(file_exists_errors)} workers: "
        f"{file_exists_errors}"
    )

    # All workers should succeed
    assert success_count.value == num_workers, (
        f"Expected {num_workers} successes, got {success_count.value}. "
        f"Errors: {errors}"
    )


def test_toctou_race_simulated_with_path_mock(tmp_path) -> None:
    """Issue #6590: Simulated TOCTOU race condition by patching Path.

    This test deterministically simulates the race condition by making
    Path.exists() return False while the directory actually exists,
    which is exactly what happens in a TOCTOU race.

    Before fix: FileExistsError is raised when mkdir is called with exist_ok=False
    After fix: No error (exist_ok=True handles it gracefully)
    """
    from unittest.mock import patch

    new_path = tmp_path / "raced_dir" / "todo.json"
    parent = new_path.parent

    # Pre-create the directory (simulating what another process would do
    # between our check and mkdir call)
    parent.mkdir(parents=True, exist_ok=True)

    original_exists = Path.exists

    def mock_exists(self):
        """Return False for our specific parent path to simulate TOCTOU race."""
        if self == parent:
            return False  # Lie: say directory doesn't exist
        return original_exists(self)

    # With the fix (exist_ok=True), this should NOT raise even though
    # the directory now exists (simulated race)
    with patch.object(Path, "exists", mock_exists):
        # This should NOT raise FileExistsError after the fix
        # because exist_ok=True handles the case where directory already exists
        _ensure_parent_directory(new_path)

    # Verify directory still exists
    assert parent.exists()


def test_exist_ok_false_demonstrates_race_bug(tmp_path) -> None:
    """Issue #6590: Demonstrates that exist_ok=False fails in race conditions.

    This test demonstrates the exact buggy pattern that exists in the code:
    checking if directory exists, then calling mkdir with exist_ok=False.
    This will fail if another process creates the directory in between.
    """
    from unittest.mock import patch

    new_path = tmp_path / "race_demo" / "todo.json"
    parent = new_path.parent

    # Pre-create the directory (simulating what another process would do)
    parent.mkdir(parents=True, exist_ok=True)

    original_exists = Path.exists

    def mock_exists_returns_false(self):
        """Always return False to simulate TOCTOU race condition."""
        if self == parent:
            return False  # Lie: say directory doesn't exist when it does
        return original_exists(self)

    # Demonstrate the buggy pattern: check then mkdir with exist_ok=False
    with patch.object(Path, "exists", mock_exists_returns_false):
        # The buggy code pattern:
        if not parent.exists():  # Returns False due to mock (TOCTOU: Time of Check)
            # But directory actually exists (TOCTOU: Time of Use)
            # exist_ok=False will raise FileExistsError
            with pytest.raises(FileExistsError):
                parent.mkdir(parents=True, exist_ok=False)

    # Now demonstrate the fix: exist_ok=True handles this gracefully
    with patch.object(Path, "exists", mock_exists_returns_false):
        if not parent.exists():  # Returns False due to mock
            # With exist_ok=True, no error even though directory exists
            parent.mkdir(parents=True, exist_ok=True)  # Should NOT raise


def test_single_process_behavior_unchanged(tmp_path) -> None:
    """Issue #6590: Single process behavior should remain unchanged after fix.

    Verify that changing exist_ok=False to exist_ok=True doesn't break
    the expected behavior for single-process use cases.
    """
    # Test 1: Creating new directory should work
    new_path = tmp_path / "new_dir" / "todo.json"
    _ensure_parent_directory(new_path)
    assert new_path.parent.exists()
    assert new_path.parent.is_dir()

    # Test 2: Calling again on existing directory should be idempotent
    _ensure_parent_directory(new_path)  # Should not raise
    assert new_path.parent.exists()

    # Test 3: Nested directory creation should work
    deep_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"
    _ensure_parent_directory(deep_path)
    assert deep_path.parent.exists()

    # Test 4: File as parent should still raise ValueError
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")
    bad_path = blocking_file / "subdir" / "todo.json"

    with pytest.raises(ValueError, match=r"(directory|not a directory)"):
        _ensure_parent_directory(bad_path)
