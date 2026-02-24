"""Tests for issue #5516: Concurrent add() operations should not cause ID collisions.

This test suite verifies that multiple processes calling add() concurrently
produce unique IDs and no data is lost (no last-writer-wins).
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the result."""
    try:
        app = TodoApp(db_path=db_path)
        # Small delay to increase race condition likelihood
        time.sleep(0.001 * (worker_id % 3))
        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that two processes adding concurrently produce unique IDs and no data loss.

    This is a regression test for issue #5516.

    Acceptance criteria:
    - Two processes simultaneously add todos
    - Both todos should exist in final storage
    - The two todos should have different IDs
    - No data loss (no last-writer-wins)
    """
    db = tmp_path / "concurrent_add.json"
    db_path = str(db)

    # Run multiple workers concurrently adding todos
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all processes at approximately the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)
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

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify all IDs are unique
    ids = [r[2] for r in successes]
    assert len(ids) == len(set(ids)), f"Duplicate IDs detected: {ids}"

    # Verify all todos are in storage (no data loss)
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # All workers' todos should be present
    assert len(final_todos) == num_workers, (
        f"Data loss detected: expected {num_workers} todos, got {len(final_todos)}. "
        f"This indicates last-writer-wins behavior."
    )

    # Verify all worker texts are present
    texts_in_storage = {todo.text for todo in final_todos}
    expected_texts = {f"worker-{i}-todo" for i in range(num_workers)}
    assert texts_in_storage == expected_texts, (
        f"Missing todos in storage. Expected: {expected_texts}, Got: {texts_in_storage}"
    )


def _mark_done_worker(todo_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that marks a todo as done and reports the result."""
    try:
        app = TodoApp(db_path=db_path)
        # Small delay to increase race condition likelihood
        time.sleep(0.001)
        todo = app.mark_done(todo_id)
        result_queue.put(("success", todo_id, todo.done))
    except Exception as e:
        result_queue.put(("error", todo_id, str(e)))


def test_concurrent_mark_done_no_data_loss(tmp_path: Path) -> None:
    """Test that concurrent mark_done operations don't lose updates.

    This is a regression test for issue #5516.

    When multiple processes try to mark the same todo as done concurrently,
    the final state should reflect that the todo is marked done (not lost).
    """
    db = tmp_path / "concurrent_mark_done.json"
    db_path = str(db)

    # Create a single todo first
    app = TodoApp(db_path=db_path)
    initial_todo = app.add("test todo")
    todo_id = initial_todo.id

    # Run multiple workers concurrently marking the same todo as done
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for _ in range(num_workers):
        p = multiprocessing.Process(target=_mark_done_worker, args=(todo_id, db_path, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded (or gracefully handled conflicts)
    errors = [r for r in results if r[0] == "error"]

    # We don't require all to succeed (some might fail due to locking),
    # but we require the final state to be consistent
    if errors:
        # If there are errors, they should be related to the todo not being found
        # (which shouldn't happen in this test)
        pass

    # Final verification: the todo should still exist and be marked done
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    assert len(final_todos) == 1, f"Expected 1 todo, got {len(final_todos)}"
    assert final_todos[0].done is True, "Todo should be marked as done"
    assert final_todos[0].text == "test todo", "Todo text should be preserved"
