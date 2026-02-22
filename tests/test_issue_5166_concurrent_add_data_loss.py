"""Regression test for issue #5166: Data loss in concurrent add scenario.

This test verifies that concurrent add operations preserve all todos
and don't silently lose data due to last-writer-wins behavior.

The fix implements file locking to serialize concurrent add operations.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Test that concurrent add operations preserve all todos.

    Verification criteria from issue #5166:
    - Create initial todo
    - Run 3 concurrent add operations
    - Verify all 4 todos (1 initial + 3 new) are present in file
    """
    db = tmp_path / "test.json"

    # Create initial todo
    app = TodoApp(db_path=str(db))
    app.add("initial todo")

    # Number of concurrent add operations
    num_concurrent = 3

    def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports result."""
        try:
            app = TodoApp(db_path=db_path)
            todo = app.add(f"worker-{worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run concurrent add operations
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_concurrent):
        p = multiprocessing.Process(target=add_worker, args=(i, str(db), result_queue))
        processes.append(p)

    # Start all processes nearly simultaneously
    for p in processes:
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Report errors for debugging
    if errors:
        error_details = "\n".join(f"  Worker {r[1]}: {r[2]}" for r in errors)
        pytest.fail(f"Some workers failed:\n{error_details}")

    assert len(successes) == num_concurrent, (
        f"Expected {num_concurrent} successes, got {len(successes)}"
    )

    # CRITICAL: Verify all todos are present
    # This is the main verification criteria from issue #5166
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # We expect: 1 initial + num_concurrent new = num_concurrent + 1 todos
    expected_count = 1 + num_concurrent
    actual_count = len(final_todos)

    assert actual_count == expected_count, (
        f"DATA LOSS DETECTED: Expected {expected_count} todos "
        f"(1 initial + {num_concurrent} concurrent adds), "
        f"but only {actual_count} remain. "
        f"This indicates last-writer-wins data loss.\n"
        f"Remaining todos: {[t.text for t in final_todos]}"
    )

    # Verify the initial todo is present
    initial_texts = [t.text for t in final_todos]
    assert "initial todo" in initial_texts, "Initial todo was lost!"

    # Verify all worker todos are present
    for i in range(num_concurrent):
        worker_text = f"worker-{i} todo"
        assert worker_text in initial_texts, (
            f"Worker {i} todo was lost! Missing: {worker_text}"
        )


def test_concurrent_add_high_contention(tmp_path: Path) -> None:
    """Test with higher contention: 10 concurrent add operations."""
    db = tmp_path / "high_contention.json"

    # Create initial todo
    app = TodoApp(db_path=str(db))
    app.add("initial")

    num_concurrent = 10

    def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path=db_path)
            app.add(f"worker-{worker_id}")
            result_queue.put(("success", worker_id, None))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_concurrent):
        p = multiprocessing.Process(target=add_worker, args=(i, str(db), result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=60)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All should succeed
    assert len(errors) == 0, f"Workers had errors: {errors}"
    assert len(successes) == num_concurrent

    # Verify all todos preserved
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    expected_count = 1 + num_concurrent
    actual_count = len(final_todos)

    assert actual_count == expected_count, (
        f"DATA LOSS: Expected {expected_count} todos, got {actual_count}"
    )
