"""Regression test for issue #3242: Concurrent write data loss.

The TodoApp methods (add, mark_done, mark_undone, remove) follow a
load-modify-save pattern that is not atomic. When multiple processes
execute these operations concurrently, data can be lost because:

1. Process A loads todos
2. Process B loads todos (same state as A)
3. Process A adds todo X and saves
4. Process B adds todo Y and saves (overwrites A's addition)

This test verifies that file locking prevents this race condition.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp


def concurrent_add_worker(
    db_path: str,
    worker_id: int,
    num_adds: int,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker that adds multiple todos concurrently."""
    try:
        app = TodoApp(db_path)
        for i in range(num_adds):
            app.add(f"worker-{worker_id}-todo-{i}")
            # Small sleep to increase chance of race condition
            time.sleep(0.001)
        result_queue.put(("success", worker_id, num_adds))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Regression test: Two processes adding todos should not lose data.

    When two processes simultaneously call add(), both todos should be
    persisted, not just the last one to save.
    """
    db_path = str(tmp_path / "concurrent.json")
    num_workers = 3
    adds_per_worker = 2

    # Start all workers nearly simultaneously
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=concurrent_add_worker,
            args=(db_path, worker_id, adds_per_worker, result_queue),
        )
        processes.append(p)

    # Start all workers at roughly the same time
    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify all todos were saved
    app = TodoApp(db_path)
    final_todos = app.list()

    # Each worker should have added adds_per_worker todos
    expected_total = num_workers * adds_per_worker

    # This assertion will FAIL before the fix is applied, because
    # concurrent writes will overwrite each other
    assert (
        len(final_todos) == expected_total
    ), f"Expected {expected_total} todos, but only {len(final_todos)} were saved. Data was lost due to race condition."


def test_concurrent_mark_done_and_add(tmp_path: Path) -> None:
    """Test that concurrent mark_done and add operations don't lose data.

    If one process marks a todo done while another adds a new todo,
    both changes should be reflected in the final state.
    """
    db_path = str(tmp_path / "concurrent_ops.json")

    # Pre-populate with a todo to mark done
    app = TodoApp(db_path)
    app.add("initial todo")

    def add_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            app.add("new todo from add worker")
            result_queue.put(("success", "add"))
        except Exception as e:
            result_queue.put(("error", "add", str(e)))

    def mark_done_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            time.sleep(0.001)  # Small delay to increase race likelihood
            app.mark_done(1)
            result_queue.put(("success", "mark_done"))
        except Exception as e:
            result_queue.put(("error", "mark_done", str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=add_worker, args=(result_queue,))
    p2 = multiprocessing.Process(target=mark_done_worker, args=(result_queue,))

    p1.start()
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final state
    app = TodoApp(db_path)
    final_todos = app.list()

    # Should have 2 todos: the original (marked done) and the new one
    assert len(final_todos) == 2, f"Expected 2 todos, got {len(final_todos)}"

    # Find the original todo and verify it's marked done
    original = next((t for t in final_todos if t.text == "initial todo"), None)
    assert original is not None, "Original todo was lost"
    assert original.done is True, "Original todo should be marked done"

    # Find the new todo
    new_todo = next((t for t in final_todos if t.text == "new todo from add worker"), None)
    assert new_todo is not None, "New todo was lost"


def test_sequential_adds_always_work(tmp_path: Path) -> None:
    """Sanity check: Sequential adds should always work (no race condition)."""
    db_path = str(tmp_path / "sequential.json")
    app = TodoApp(db_path)

    for i in range(10):
        app.add(f"todo-{i}")

    final_todos = app.list()
    assert len(final_todos) == 10

    texts = {t.text for t in final_todos}
    for i in range(10):
        assert f"todo-{i}" in texts
