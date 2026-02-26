"""Regression tests for issue #5929: TOCTOU race condition in _ensure_parent_directory.

Issue: _ensure_parent_directory checks if parent.exists() then calls mkdir(exist_ok=False).
In a race condition, another process could create the directory between the check and mkdir,
causing FileExistsError instead of gracefully handling the situation.

These tests verify that concurrent saves to non-existent parent directories succeed.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_ensure_parent_directory_no_race(tmp_path) -> None:
    """Regression test for issue #5929: Race condition in _ensure_parent_directory.

    Simulates two processes calling _ensure_parent_directory concurrently on the same
    non-existent directory. Both should succeed - one creates, the other uses exist_ok=True
    to ignore the fact that the directory now exists.
    """
    # Path with non-existent parent
    test_path = tmp_path / "new_dir" / "subdir" / "file.json"
    assert not test_path.parent.exists(), "Parent should not exist at start"

    results = multiprocessing.Manager().list()

    def worker(worker_id: int) -> None:
        """Worker that calls _ensure_parent_directory."""
        try:
            # Small delay to increase race condition likelihood
            time.sleep(0.001 * worker_id)
            _ensure_parent_directory(test_path)
            results.append(("success", worker_id))
        except Exception as e:
            results.append(("error", worker_id, str(e)))

    # Run workers concurrently
    processes = []
    for i in range(3):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # All workers should succeed
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers failed with race condition: {errors}"
    assert len(results) == 3, f"Expected 3 successes, got {len(results)}"


def test_ensure_parent_directory_handles_simulated_race_condition(tmp_path) -> None:
    """Test that _ensure_parent_directory handles race condition by using exist_ok=True.

    This test simulates the race condition by mocking mkdir to fail the first time
    with FileExistsError (as if another process created the directory), and verifies
    that the function handles this gracefully.
    """
    test_path = tmp_path / "raced_dir" / "file.json"

    # First call will raise FileExistsError (simulating race)
    # Second call should succeed because directory now exists
    call_count = 0
    original_mkdir = Path.mkdir

    def mock_mkdir(self, parents=False, exist_ok=False):
        nonlocal call_count
        call_count += 1
        if call_count == 1 and not exist_ok:
            # Simulate race: another process created the directory
            # Create it for real so subsequent checks work
            original_mkdir(self, parents=parents, exist_ok=True)
            # Raise as if we lost the race
            raise FileExistsError(f"[Errno 17] File exists: '{self}'")
        # On subsequent calls, proceed normally
        return original_mkdir(self, parents=parents, exist_ok=True)

    with patch.object(Path, "mkdir", mock_mkdir):
        # This should NOT raise FileExistsError after fix
        _ensure_parent_directory(test_path)

    # Verify directory was created
    assert test_path.parent.exists()


def test_concurrent_save_to_new_directory_no_error(tmp_path) -> None:
    """Regression test for issue #5929: Concurrent save() to non-existent parent directory.

    Two processes saving to a path where the parent directory doesn't exist should both
    succeed without FileExistsError.
    """
    # Path with non-existent parent directory
    db_path = tmp_path / "concurrent_new_dir" / "todo.json"
    assert not db_path.parent.exists(), "Parent directory should not exist initially"

    results = multiprocessing.Manager().list()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to a new directory path."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            results.append(("success", worker_id))
        except Exception as e:
            results.append(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    processes = []
    for i in range(3):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # All workers should succeed without FileExistsError
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers failed due to race condition: {errors}"
    assert len(results) == 3, f"Expected 3 successes, got {len(results)}"

    # Verify file contains valid data
    storage = TodoStorage(str(db_path))
    loaded = storage.load()
    assert len(loaded) >= 1, "Should have at least one todo"
