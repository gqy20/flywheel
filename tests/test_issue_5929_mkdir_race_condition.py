"""Regression test for issue #5929: TOCTOU race condition in _ensure_parent_directory.

This test verifies that concurrent processes creating a new parent directory
for the database file do not fail due to FileExistsError when the directory
is created by another process between the existence check and mkdir call.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_parent_directory_creation_no_race_condition(tmp_path) -> None:
    """Regression test for issue #5929.

    Tests that multiple processes concurrently saving to a database file
    whose parent directory does NOT exist yet should all succeed without
    FileExistsError.

    Before the fix: If process A checks parent.exists() -> False, then
    process B creates the directory, process A's mkdir(exist_ok=False)
    would raise FileExistsError.

    After the fix: Using exist_ok=True handles the race condition gracefully.
    """
    # Create a path where parent directory doesn't exist yet
    new_dir = tmp_path / "nonexistent_parent_dir"
    db = new_dir / "todo.json"

    # Ensure parent doesn't exist
    assert not new_dir.exists(), "Parent directory should not exist initially"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves to a new directory path."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}-data")]

            # Small delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))

            storage.save(todos)

            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug we're testing for - should NOT happen after fix
            result_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently that all need to create the parent dir
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for FileExistsError specifically (the bug)
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    assert len(file_exists_errors) == 0, (
        f"FileExistsError occurred due to race condition: {file_exists_errors}. "
        "This indicates the TOCTOU bug in _ensure_parent_directory is not fixed."
    )

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    other_errors = [r for r in results if r[0] == "error"]

    assert len(other_errors) == 0, f"Unexpected errors: {other_errors}"
    assert len(successes) >= 1, "At least one worker should have succeeded"

    # Parent directory should now exist
    assert new_dir.exists(), "Parent directory should exist after saves"

    # File should contain valid data from one of the workers
    storage = TodoStorage(str(db))
    loaded = storage.load()
    assert len(loaded) >= 1
    assert all(hasattr(t, "id") and hasattr(t, "text") for t in loaded)


def test_ensure_parent_directory_race_condition_simulated(tmp_path, monkeypatch) -> None:
    """Unit test that demonstrates and verifies the fix for issue #5929.

    This test simulates the race condition where:
    1. parent.exists() returns False (we check)
    2. Another process creates the directory between our check and mkdir
    3. Our mkdir should not fail because exist_ok=True (the fix)
    """
    # Create a path where parent doesn't exist
    new_dir = tmp_path / "race_test_dir"
    db = new_dir / "todo.json"

    # Track the original mkdir method
    original_mkdir = Path.mkdir
    mkdir_calls = []

    def mkdir_with_race_condition(self, *args, **kwargs):
        """Mock mkdir that simulates another process creating the dir first."""
        exist_ok = kwargs.get("exist_ok", False)
        parents = kwargs.get("parents", False)
        mkdir_calls.append({"path": str(self), "exist_ok": exist_ok, "parents": parents})

        # Simulate the race: another process creates the directory before our mkdir
        # This happens between _ensure_parent_directory's exists() check and mkdir call
        if not self.exists():
            original_mkdir(self, parents=parents, exist_ok=True)

        # Now call the original mkdir with the original exist_ok value
        # If exist_ok=False (the bug), this will raise FileExistsError
        # If exist_ok=True (the fix), it will succeed
        return original_mkdir(self, *args, **kwargs)

    # Patch Path.mkdir to simulate the race
    monkeypatch.setattr(Path, "mkdir", mkdir_with_race_condition)

    # This should succeed with exist_ok=True fix
    # Before fix: exist_ok=False would cause FileExistsError
    # After fix: exist_ok=True should succeed
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify mkdir was called with exist_ok=True (the fix)
    assert len(mkdir_calls) >= 1, "mkdir should have been called"
    # The fix ensures exist_ok=True is used
    for call in mkdir_calls:
        if call["parents"] is True:
            assert call["exist_ok"] is True, (
                f"mkdir should be called with exist_ok=True to avoid race condition, "
                f"got exist_ok={call['exist_ok']}"
            )

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
