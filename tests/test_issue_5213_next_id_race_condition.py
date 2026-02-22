"""Regression test for issue #5213: Race condition in next_id().

This test verifies that multiple concurrent calls to add() produce unique IDs.
The bug was that next_id() computed new IDs based on the current todos list,
so two processes reading the same list would generate the same ID.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is the regression test for issue #5213.
    Two processes adding todos concurrently should NOT produce duplicate IDs.
    """
    db = tmp_path / "todos.json"
    num_workers = 10
    num_adds_per_worker = 5

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds multiple todos and reports their IDs."""
        try:
            app = TodoApp(db_path=str(db))
            ids = []
            for i in range(num_adds_per_worker):
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                ids.append(todo.id)
            result_queue.put(("success", worker_id, ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Collect all IDs from successful workers
    all_ids: list[int] = []
    successes = [r for r in results if r[0] == "success"]
    for success in successes:
        all_ids.extend(success[2])  # success[2] is the list of IDs

    # Verify no duplicate IDs
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs detected! "
        f"Expected {len(all_ids)} unique IDs but got {len(set(all_ids))}. "
        f"IDs: {sorted(all_ids)}"
    )


def test_next_id_with_file_lock_produces_unique_ids(tmp_path: Path) -> None:
    """Test that using file lock for next_id produces unique IDs.

    This test verifies the fix: next_id() should use file-based locking
    to ensure ID uniqueness across concurrent processes.
    """
    db = tmp_path / "todos.json"

    # Create storage and add initial todo
    storage = TodoStorage(str(db))
    initial_todos = [Todo(id=1, text="initial")]
    storage.save(initial_todos)

    # Create multiple todos concurrently and verify IDs are unique
    num_workers = 5
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    def next_id_worker(worker_id: int, queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path=str(db))
            # Each worker adds multiple todos
            ids = []
            for i in range(3):
                todo = app.add(f"concurrent-{worker_id}-{i}")
                ids.append(todo.id)
            queue.put(("success", worker_id, ids))
        except Exception as e:
            queue.put(("error", worker_id, str(e)))

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=next_id_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect all IDs
    all_ids: list[int] = []
    while not result_queue.empty():
        result = result_queue.get()
        if result[0] == "success":
            all_ids.extend(result[2])

    # All IDs should be unique
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs found: {sorted(all_ids)}"
    )


def test_load_time_id_detection(tmp_path: Path) -> None:
    """Test that loading todos with duplicate IDs is handled gracefully.

    Even with the fix, if duplicate IDs somehow get into the file,
    the next_id() should still work correctly by finding the max ID.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Manually create a file with duplicate IDs (simulating the bug)
    import json
    duplicate_data = [
        {"id": 1, "text": "first"},
        {"id": 1, "text": "duplicate"},  # Same ID!
        {"id": 2, "text": "second"},
    ]
    db.write_text(json.dumps(duplicate_data))

    # next_id should still work - it finds the max ID
    todos = storage.load()
    next_id = storage.next_id(todos)

    # Should be max(1, 1, 2) + 1 = 3
    assert next_id == 3, f"Expected next_id=3, got {next_id}"


def test_single_process_unique_ids(tmp_path: Path) -> None:
    """Sanity test: single process should always produce unique IDs."""
    db = tmp_path / "todos.json"
    app = TodoApp(db_path=str(db))

    ids = []
    for i in range(100):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # All IDs should be unique
    assert len(ids) == len(set(ids)), f"Duplicate IDs in single process: {ids}"
    # IDs should start from 1 and be sequential
    assert sorted(ids) == list(range(1, 101))
