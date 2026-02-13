"""Tests for issue #3041: Race condition in CLI add operation.

This test suite verifies that concurrent add operations from multiple processes
do not cause ID collisions or data loss.
"""

from __future__ import annotations

import multiprocessing

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Regression test for issue #3041: Concurrent adds must produce unique IDs.

    This test spawns multiple processes that each add a todo to the same database
    file concurrently. After all processes complete:
    - All todo IDs must be unique (no collisions)
    - No data loss should occur (all todos should be present)
    """
    db = tmp_path / "concurrent.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the result."""
        try:
            app = TodoApp(str(db))
            # Each worker adds a unique todo
            todo = app.add(f"worker-{worker_id}-todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
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

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify that all IDs are unique
    ids = [r[2] for r in successes]
    assert len(ids) == len(set(ids)), f"ID collision detected! IDs: {ids}, unique IDs: {set(ids)}"

    # Verify final state - all todos should be present (no data loss)
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All workers' todos should be in the final state
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(final_todos)}. Data loss may have occurred."
    )

    # Verify each worker's todo text is present
    todo_texts = {t.text for t in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-todo"
        assert expected_text in todo_texts, f"Missing todo from worker {i}: {expected_text}"


def test_concurrent_add_with_existing_todos(tmp_path) -> None:
    """Test concurrent adds when there are existing todos.

    Verifies that the fix works correctly when the database already has todos.
    """
    db = tmp_path / "concurrent_with_existing.json"

    # Create initial state with a few todos
    storage = TodoStorage(str(db))
    initial_todos = [
        Todo(id=1, text="initial-1"),
        Todo(id=2, text="initial-2"),
    ]
    storage.save(initial_todos)

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the result."""
        try:
            app = TodoApp(str(db))
            todo = app.add(f"concurrent-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Verify unique IDs
    ids = [r[2] for r in successes]
    assert len(ids) == len(set(ids)), f"ID collision detected! IDs: {ids}"

    # Verify final state includes both initial and new todos
    final_todos = storage.load()
    assert len(final_todos) == 2 + num_workers, (
        f"Expected {2 + num_workers} todos (2 initial + {num_workers} new), got {len(final_todos)}"
    )

    # Verify initial todos are preserved
    final_texts = {t.text for t in final_todos}
    assert "initial-1" in final_texts
    assert "initial-2" in final_texts

    # Verify concurrent todos are present
    for i in range(num_workers):
        assert f"concurrent-{i}" in final_texts
