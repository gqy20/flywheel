"""Regression test for issue #1925: Race condition in concurrent save operations.

This test verifies that concurrent save operations from multiple processes
do not cause data loss due to non-atomic read-modify-write cycles.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def _add_todo_worker(db_path: Path, todo_id: int, text: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo to the shared storage.

    Each worker calls add_todo() which holds the lock during the entire
    read-modify-write cycle, preventing race conditions.
    """
    storage = TodoStorage(str(db_path))
    storage.add_todo(Todo(id=todo_id, text=text))
    result_queue.put(todo_id)


def test_concurrent_saves_from_multiple_processes_no_data_loss(tmp_path) -> None:
    """Test that concurrent save operations from multiple processes don't lose data.

    This test spawns multiple processes that each:
    1. Read the current todo list
    2. Add a new todo
    3. Write back

    Without file locking, the last writer wins and intermediate updates are lost.
    With proper file locking, all updates should be preserved.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial empty state
    storage.save([])

    # Number of concurrent workers
    num_workers = 5
    result_queue = multiprocessing.Queue()

    # Spawn processes that will race to add their todos
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=_add_todo_worker,
            args=(db, i + 1, f"todo-{i+1}", result_queue)
        )
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Check for any process failures
    failed = [p for p in processes if p.exitcode != 0]
    assert not failed, f"Some processes failed: {[p.exitcode for p in failed]}"

    # Load final state
    final_todos = storage.load()

    # All todos should be present (no data loss)
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, but got {len(final_todos)}. "
        f"Data loss occurred due to race condition. "
        f"Todos: {[t.text for t in final_todos]}"
    )

    # Verify all unique todo IDs are present
    todo_ids = {todo.id for todo in final_todos}
    assert todo_ids == set(range(1, num_workers + 1)), (
        f"Missing todo IDs: {set(range(1, num_workers + 1)) - todo_ids}"
    )


def test_concurrent_saves_preserve_all_data(tmp_path) -> None:
    """Simpler test: two processes adding todos concurrently."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start with one todo
    storage.save([Todo(id=1, text="initial")])

    result_queue = multiprocessing.Queue()
    p1 = multiprocessing.Process(
        target=_add_todo_worker,
        args=(db, 2, "from-process-1", result_queue)
    )
    p2 = multiprocessing.Process(
        target=_add_todo_worker,
        args=(db, 3, "from-process-2", result_queue)
    )

    p1.start()
    p2.start()
    p1.join()
    p2.join()

    assert p1.exitcode == 0, f"Process 1 failed with exit code {p1.exitcode}"
    assert p2.exitcode == 0, f"Process 2 failed with exit code {p2.exitcode}"

    # Should have 3 todos: initial + 2 added
    final_todos = storage.load()
    assert len(final_todos) == 3, (
        f"Expected 3 todos, got {len(final_todos)}. Data loss occurred!"
    )
