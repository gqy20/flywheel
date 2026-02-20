"""Regression tests for issue #4790: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition between exists() check and mkdir() call in _ensure_parent_directory.
Two concurrent processes calling save() simultaneously should not raise FileExistsError.

These tests verify the fix using exist_ok=True in mkdir() to handle the race gracefully.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_directory_creation_no_file_exists_error(tmp_path) -> None:
    """Regression test for issue #4790: Concurrent saves to non-existent parent directory.

    Two concurrent processes calling save() on a path with non-existent parent
    directory should not raise FileExistsError due to TOCTOU race condition
    between exists() check and mkdir() call.
    """

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves to a path with non-existent parent directory."""
        try:
            # Each worker uses same db path - parent dir doesn't exist initially
            db_path = tmp_path / "shared_parent" / "todos.json"
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id, None))
        except FileExistsError as e:
            # This is the bug we're testing for - should NOT happen after fix
            result_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently - all will try to create parent dir at same time
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        # Start all processes nearly simultaneously to maximize race condition
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for FileExistsError - this is the TOCTOU bug
    file_exists_errors = [r for r in results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race condition detected! FileExistsError raised: {file_exists_errors}"
    )

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] not in ("success", "FileExistsError")]

    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. Errors: {errors}"
    )


def test_concurrent_directory_creation_with_staggered_start(tmp_path) -> None:
    """Test with small stagger to maximize race window overlap."""

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        try:
            db_path = tmp_path / "staggered_parent" / "db.json"
            storage = TodoStorage(str(db_path))
            # Small stagger to ensure overlap in mkdir attempts
            time.sleep(0.001 * (worker_id % 3))
            todos = [Todo(id=worker_id, text=f"staggered-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id, None))
        except FileExistsError as e:
            result_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 8
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    file_exists_errors = [r for r in results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race condition with staggered start: {file_exists_errors}"
    )

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers


def test_directory_creation_idempotent_after_creation(tmp_path) -> None:
    """Test that _ensure_parent_directory is idempotent after directory exists.

    After one process creates the directory, subsequent calls should not fail.
    """
    db_path = tmp_path / "idempotent_test" / "todos.json"
    storage1 = TodoStorage(str(db_path))
    storage2 = TodoStorage(str(db_path))

    # First save creates directory
    storage1.save([Todo(id=1, text="first")])

    # Second save should work fine (directory already exists)
    storage2.save([Todo(id=2, text="second")])

    # Verify both saves worked
    loaded = storage1.load()
    assert len(loaded) == 1  # Last write wins
    assert loaded[0].text == "second"


def test_deeply_nested_concurrent_creation(tmp_path) -> None:
    """Test concurrent creation of deeply nested directory structure."""

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        try:
            # Deeply nested path that doesn't exist
            db_path = (
                tmp_path / "deep" / "nested" / f"worker_{worker_id}" / "data" / "todos.json"
            )
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"deep-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id, None))
        except FileExistsError as e:
            result_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    file_exists_errors = [r for r in results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race in nested path creation: {file_exists_errors}"
    )

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers


def test_toctou_race_condition_direct_simulation(tmp_path) -> None:
    """Direct test of TOCTOU race condition via mock injection.

    This test simulates the race condition by having another process
    create the directory between the exists() check and mkdir() call.
    """
    import threading

    db_path = tmp_path / "race_test" / "todos.json"
    parent = db_path.parent

    race_triggered = threading.Event()
    mkdir_calls = []

    # Save original mkdir
    original_mkdir = Path.mkdir

    def racing_mkdir(self, *args, **kwargs):
        # Track calls
        mkdir_calls.append(self)

        # If this is our target parent directory and it doesn't exist yet,
        # simulate race by having another thread create it first
        if self == parent and not parent.exists():
            # Create directory from "another process"
            original_mkdir(self, parents=True, exist_ok=True)
            race_triggered.set()

        # Call original - with exist_ok=False this would fail before fix
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", racing_mkdir):
        storage = TodoStorage(str(db_path))

        # This should NOT raise FileExistsError after fix
        # Before fix, mkdir(exist_ok=False) would fail since directory already exists
        storage.save([Todo(id=1, text="test")])

    # Verify the race was actually triggered
    assert race_triggered.is_set(), "Race condition simulation should have been triggered"

    # Verify the save worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
