"""Regression tests for issue #5929: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function checks if parent.exists() and then
calls mkdir(parents=True, exist_ok=False). This creates a race condition window
where another process could create the directory between the check and mkdir,
causing FileExistsError.

Acceptance criteria:
- When two processes concurrently call save() with a non-existent parent directory,
  both should succeed (one creates, the other uses exist_ok=True to ignore).
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_handles_race_condition(tmp_path) -> None:
    """Test that _ensure_parent_directory is immune to TOCTOU race conditions.

    This test simulates a race condition by:
    1. Creating the parent directory after the exists() check but before mkdir()
    2. Verifying that _ensure_parent_directory doesn't fail with FileExistsError
    """
    import threading

    target_path = tmp_path / "subdir" / "todo.json"
    race_triggered = threading.Event()
    mkdir_attempts = []

    # Track mkdir calls to simulate race condition
    original_mkdir = Path.mkdir

    def race_mkdir(self, *args, **kwargs):
        mkdir_attempts.append(self)

        # On first mkdir to our target parent, simulate race:
        # Create the directory before the actual mkdir is called
        if self == target_path.parent and not race_triggered.is_set():
            race_triggered.set()
            # Create the directory (simulating another process)
            original_mkdir(self, parents=True, exist_ok=True)

        # Call original mkdir - if exist_ok=False, this would fail without the fix
        return original_mkdir(self, *args, **kwargs)

    import unittest.mock

    with unittest.mock.patch.object(Path, "mkdir", race_mkdir):
        # This should NOT raise FileExistsError even with the race condition
        _ensure_parent_directory(target_path)

    # Verify the parent directory was created
    assert target_path.parent.exists()
    assert race_triggered.is_set(), "Race condition simulation should have triggered"


def test_concurrent_save_to_nonexistent_directory_succeeds(tmp_path) -> None:
    """Regression test: Multiple processes saving to new directory should all succeed.

    This is the acceptance test from the issue:
    - Two processes concurrently call save() where parent directory doesn't exist
    - Both should succeed (one creates directory, other uses exist_ok=True)
    """
    import time

    db = tmp_path / "newdir" / "deep" / "concurrent.json"

    # Ensure parent doesn't exist
    assert not db.parent.exists()

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos to a path with non-existent parent directory."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=1, text=f"worker-{worker_id}-data")]
            storage.save(todos)

            # Small delay to increase race condition likelihood
            time.sleep(0.001)

            # Verify we can read back valid data
            loaded = storage.load()
            result_queue.put(("success", worker_id, len(loaded)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors (especially FileExistsError)
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # The key assertion: no FileExistsError should occur
    file_exists_errors = [e for e in errors if "FileExistsError" in str(e[2])]
    assert len(file_exists_errors) == 0, (
        f"Workers encountered FileExistsError (race condition bug): {file_exists_errors}"
    )

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Final verification: file should exist and be valid
    assert db.exists(), "Database file should exist after concurrent saves"
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    assert len(final_todos) >= 1, "Should have at least one todo"


def test_ensure_parent_directory_with_existing_parent_is_idempotent(tmp_path) -> None:
    """Test that calling _ensure_parent_directory multiple times is safe."""
    target_path = tmp_path / "existing_dir" / "todo.json"

    # Call multiple times - should not raise
    _ensure_parent_directory(target_path)
    _ensure_parent_directory(target_path)
    _ensure_parent_directory(target_path)

    assert target_path.parent.exists()


def test_ensure_parent_directory_creates_deep_hierarchy(tmp_path) -> None:
    """Test that _ensure_parent_directory creates deep directory hierarchies."""
    target_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

    _ensure_parent_directory(target_path)

    assert target_path.parent.exists()
    assert (tmp_path / "a" / "b" / "c" / "d").is_dir()
