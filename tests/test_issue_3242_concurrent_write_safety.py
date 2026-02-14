"""Regression test for issue #3242: Concurrent write data loss.

This test verifies that concurrent operations on TodoApp don't lose data.
The load-modify-save pattern in add/mark_done/mark_undone/remove is not
atomic, so without proper locking, concurrent operations can lose data.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp


def test_concurrent_add_operations_no_data_loss(tmp_path: Path) -> None:
    """Test that two concurrent add operations don't lose data.

    Issue #3242: Without file locking, if two processes load the same state
    and both add a todo, the second save overwrites the first's changes.

    Expected: Both todos should be in the final state.
    """
    db_path = tmp_path / "concurrent.json"

    def add_todo_worker(todo_text: str, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo."""
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(todo_text)
            result_queue.put(("success", todo.id, todo.text))
        except Exception as e:
            result_queue.put(("error", str(e)))

    # Create two processes that both add todos concurrently
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for i in range(2):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(f"concurrent-todo-{i}", result_queue),
        )
        processes.append(p)

    # Start both processes nearly simultaneously
    for p in processes:
        p.start()

    # Wait for both to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Both operations should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Verify no errors occurred
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # Critical assertion: Both todos should be present in final state
    # Without locking, one todo will be lost due to race condition
    app = TodoApp(db_path=str(db_path))
    final_todos = app.list()

    # Extract todo texts for assertion
    todo_texts = {todo.text for todo in final_todos}

    # Both todos should be present - this is what we're testing for
    assert "concurrent-todo-0" in todo_texts, "First concurrent todo was lost!"
    assert "concurrent-todo-1" in todo_texts, "Second concurrent todo was lost!"
    assert len(final_todos) == 2, f"Expected 2 todos, got {len(final_todos)}"


def test_concurrent_add_preserves_all_data_under_contention(tmp_path: Path) -> None:
    """Stress test: Multiple concurrent adds should preserve all data.

    This is a more rigorous test that runs multiple workers adding todos
    concurrently. All todos should be present in the final state.
    """
    db_path = tmp_path / "stress_test.json"
    num_workers = 5

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo."""
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(f"worker-{worker_id}-todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(i, result_queue),
        )
        processes.append(p)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Verify all todos are present
    app = TodoApp(db_path=str(db_path))
    final_todos = app.list()
    todo_texts = {todo.text for todo in final_todos}

    # Each worker's todo should be present
    for i in range(num_workers):
        expected_text = f"worker-{i}-todo"
        assert expected_text in todo_texts, f"Todo from worker {i} was lost!"

    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(final_todos)}"
    )


def test_lock_is_released_after_operation(tmp_path: Path) -> None:
    """Test that the lock is properly released after operations complete.

    If the lock isn't released, subsequent operations would hang or fail.
    """
    db_path = tmp_path / "lock_release.json"
    app = TodoApp(db_path=str(db_path))

    # Perform multiple sequential operations
    app.add("first")
    app.add("second")
    app.mark_done(1)
    app.mark_undone(1)
    app.remove(1)

    # All should succeed without hanging
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "second"
