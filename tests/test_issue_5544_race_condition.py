"""Regression test for issue #5544: Race condition in concurrent writes.

This test suite verifies that concurrent add() operations do not lose data.
The original issue was that the read-modify-write pattern in add(), mark_done(),
etc. was not atomic, causing data loss when multiple processes wrote concurrently.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_no_data_loss_multiprocess(tmp_path: Path) -> None:
    """Regression test for #5544: Two processes adding todos concurrently must not lose data.

    This test specifically targets the race condition where:
    1. Process A loads todos (empty)
    2. Process B loads todos (empty)
    3. Process A adds todo with id=1, saves
    4. Process B adds todo with id=1 (duplicate!), saves overwriting A's todo

    After fix, both todos should be present with unique IDs.
    """
    db = tmp_path / "race_test.json"

    def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports success/failure."""
        try:
            app = TodoApp(db_path=str(db_path))
            # Each worker adds a unique todo
            todo = app.add(f"Worker {worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that all try to add concurrently
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all processes at roughly the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db), result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify final state: ALL todos must be present
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Critical assertion: no data loss!
    assert len(final_todos) == num_workers, (
        f"DATA LOSS: Expected {num_workers} todos, but only {len(final_todos)} exist. "
        f"This indicates a race condition in the add() method. "
        f"Present todos: {[t.text for t in final_todos]}"
    )

    # Verify all worker texts are present
    texts = {t.text for t in final_todos}
    for i in range(num_workers):
        assert f"Worker {i} todo" in texts, f"Missing todo from worker {i}"

    # Verify all IDs are unique
    ids = [t.id for t in final_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs detected: {ids}"


def test_concurrent_add_no_data_loss_high_contention(tmp_path: Path) -> None:
    """High-contention variant: many more workers to increase race condition likelihood."""
    db = tmp_path / "high_contention_test.json"

    def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(f"High-contention worker {worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Use more workers to increase contention
    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=15)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # No data loss under high contention
    assert len(final_todos) == num_workers, (
        f"DATA LOSS under high contention: Expected {num_workers} todos, got {len(final_todos)}"
    )


def test_concurrent_mark_done_no_data_loss(tmp_path: Path) -> None:
    """Test that concurrent mark_done operations don't lose other todos.

    Scenario:
    1. Create todos 1-3
    2. Two processes try to mark todo #1 as done concurrently
    3. After both complete, todos 2 and 3 should still exist
    """
    db = tmp_path / "mark_done_test.json"
    app = TodoApp(db_path=str(db))

    # Create initial todos
    app.add("Todo 1")
    app.add("Todo 2")
    app.add("Todo 3")

    def mark_done_worker(todo_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        try:
            worker_app = TodoApp(db_path=str(db_path))
            worker_app.mark_done(todo_id)
            result_queue.put(("success", todo_id))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Two processes try to mark todo #1 as done
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []
    for _ in range(2):
        p = multiprocessing.Process(target=mark_done_worker, args=(1, str(db), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Verify all todos still exist
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All 3 todos should still exist
    assert len(final_todos) == 3, (
        f"DATA LOSS during mark_done: Expected 3 todos, got {len(final_todos)}"
    )

    # Todo #1 should be marked done
    todo1 = next((t for t in final_todos if t.id == 1), None)
    assert todo1 is not None, "Todo #1 was lost"
    assert todo1.done is True, "Todo #1 should be marked done"
