"""Regression tests for issue #5378: TOCTOU race in _ensure_parent_directory.

Issue: The _ensure_parent_directory function has a Time-Of-Check-Time-Of-Use race
between parent.exists() check and parent.mkdir() call. If another process creates
the directory between the check and mkdir, FileExistsError is raised.

The fix should use exist_ok=True to make the operation atomic.
"""

from __future__ import annotations

import multiprocessing
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_no_toctou_race_with_barrier(tmp_path: Path) -> None:
    """Regression test for issue #5378: Concurrent _ensure_parent_directory calls.

    Uses a barrier to maximize race condition likelihood - all threads attempt
    mkdir at exactly the same moment after all pass the exists() check.
    """
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"
    num_threads = 5
    barrier = threading.Barrier(num_threads)
    errors: list[Exception] = []
    lock = threading.Lock()

    def ensure_parent_worker() -> None:
        """Worker that synchronizes and calls _ensure_parent_directory."""
        try:
            # Wait for all threads to be ready
            barrier.wait(timeout=5)
            # All threads try at once
            _ensure_parent_directory(db_path)
        except threading.BrokenBarrierError:
            pass  # Barrier timeout, not the issue we're testing
        except Exception as e:
            with lock:
                errors.append(e)

    # Start all threads
    threads = [threading.Thread(target=ensure_parent_worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # No FileExistsError should occur
    file_exists_errors = [e for e in errors if isinstance(e, FileExistsError)]
    assert len(file_exists_errors) == 0, f"TOCTOU race triggered FileExistsError: {file_exists_errors}"

    # Parent directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_ensure_parent_directory_toctou_race_simulated(tmp_path: Path) -> None:
    """Simulate TOCTOU race by mocking mkdir to raise FileExistsError after exists() check.

    This test directly exposes the bug: if exists() returns False but mkdir() finds
    the directory already exists (race condition), the current code raises FileExistsError.
    """
    db_path = tmp_path / "racedir" / "todo.json"
    original_mkdir = Path.mkdir

    def racing_mkdir(self: Path, *args, **kwargs) -> None:
        """Simulate another process creating the directory during the race window."""
        # If this is the parent directory we're trying to create
        if self == db_path.parent and not self.exists():
            # Simulate concurrent creation
            original_mkdir(self, parents=True, exist_ok=True)
        # Now call the original with exist_ok=False (the buggy behavior)
        kwargs_copy = kwargs.copy()
        kwargs_copy.pop("exist_ok", None)  # Remove if present
        kwargs_copy["exist_ok"] = False  # Force False to expose bug
        return original_mkdir(self, *args, **{k: v for k, v in kwargs_copy.items() if k != "exist_ok"} | {"exist_ok": False})

    with patch.object(Path, "mkdir", racing_mkdir):
        # This should NOT raise FileExistsError after the fix
        try:
            _ensure_parent_directory(db_path)
        except FileExistsError as e:
            pytest.fail(f"TOCTOU race triggered FileExistsError: {e}")


def test_concurrent_save_to_new_path_no_toctou_race(tmp_path: Path) -> None:
    """End-to-end test: Concurrent save() to same new path should not raise FileExistsError."""
    from flywheel.storage import TodoStorage

    db_path = tmp_path / "concurrent_new" / "todo.json"
    results_queue: multiprocessing.Queue = multiprocessing.Queue()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to a new path."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            results_queue.put(("success", worker_id))
        except Exception as e:
            results_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 3
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    errors = [r for r in results if r[0] == "error"]

    # No worker should get FileExistsError
    assert len(errors) == 0, f"Concurrent saves hit race condition: {errors}"


def test_ensure_parent_directory_still_validates_file_conflict(tmp_path: Path) -> None:
    """Verify that the fix doesn't break file-as-directory validation."""
    # Create a file where a directory should be
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("I am a file")

    # This path would require the file to be a directory
    db_path = conflicting_file / "subdir" / "todo.json"

    # Should still raise ValueError for file-as-directory conflict
    with pytest.raises(ValueError, match=r"(file|directory)"):
        _ensure_parent_directory(db_path)
