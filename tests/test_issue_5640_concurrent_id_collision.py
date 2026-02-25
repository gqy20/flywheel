"""Regression test for issue #5640: Duplicate ID generation in concurrent add operations.

This test verifies that concurrent add operations from multiple processes
produce unique IDs without data loss or corruption from ID collisions.

The bug occurs because:
1. Process A calls load() and sees empty list, next_id() returns 1
2. Process B calls load() and sees empty list, next_id() returns 1 (duplicate!)
3. Process A saves with id=1
4. Process B saves with id=1 (overwrites Process A's todo or loses B's todo)
"""

from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp


def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the generated ID."""
    try:
        app = TodoApp(db_path=db_path)
        # Small delay to increase race condition likelihood
        # All workers start nearly simultaneously
        time.sleep(0.001 * (worker_id % 3))

        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_operations_produce_unique_ids(tmp_path) -> None:
    """Regression test for issue #5640: Concurrent add operations must produce unique IDs.

    This test creates multiple processes that each call add() concurrently.
    Without proper locking, these processes could generate duplicate IDs,
    leading to data loss or corruption.
    """
    db_path = str(tmp_path / "concurrent.json")

    # Run multiple workers that each add a todo concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Collect all generated IDs
    generated_ids = [r[2] for r in successes]

    # CRITICAL: All IDs must be unique
    unique_ids = set(generated_ids)
    assert len(unique_ids) == num_workers, (
        f"Duplicate IDs detected! Generated IDs: {generated_ids}, "
        f"Unique IDs: {unique_ids}. "
        f"This indicates a race condition in concurrent add operations."
    )

    # Verify the file contains valid JSON with all todos
    db_file = Path(db_path)
    raw_content = db_file.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    # All todos should be present in the file
    assert len(parsed) == num_workers, (
        f"Expected {num_workers} todos in file, but found {len(parsed)}. "
        f"Some todos may have been lost due to concurrent write conflicts."
    )

    # All IDs in file should also be unique
    file_ids = [todo["id"] for todo in parsed]
    assert len(set(file_ids)) == num_workers, (
        f"Duplicate IDs in file! File IDs: {file_ids}"
    )

    # Each worker's todo should be present
    file_texts = {todo["text"] for todo in parsed}
    for i in range(num_workers):
        expected_text = f"worker-{i}-todo"
        assert expected_text in file_texts, f"Missing todo from worker {i}"


def test_concurrent_add_preserves_all_todos_under_contention(tmp_path) -> None:
    """Additional test: Verify no data loss even under heavy contention.

    This test adds more workers to increase contention and verify
    that all todos are preserved with unique IDs.
    """
    db_path = str(tmp_path / "heavy_contention.json")

    # More workers for heavier contention
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # All IDs must be unique
    generated_ids = [r[2] for r in successes]
    unique_ids = set(generated_ids)
    assert len(unique_ids) == num_workers, (
        f"Duplicate IDs detected under heavy contention! "
        f"Generated IDs: {generated_ids}"
    )

    # Verify all todos are in the file
    app = TodoApp(db_path=db_path)
    all_todos = app.list()
    assert len(all_todos) == num_workers, (
        f"Data loss detected! Expected {num_workers} todos, found {len(all_todos)}"
    )
