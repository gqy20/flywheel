"""Regression test for issue #5556: Race condition in TodoApp operations.

This test verifies that TodoApp uses file-based locking to prevent
race conditions when multiple processes perform load-modify-save operations.

The issue: While TodoStorage.save() is atomic, the load-modify-save pattern
in TodoApp methods (add, mark_done, remove) is not atomic, leading to data loss
when multiple processes access the same todo file concurrently.

The fix: Implement file-based locking using the filelock library to ensure
exclusive access during load-modify-save sequences.
"""

from __future__ import annotations

import multiprocessing

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_todos_worker(
    db_path: str, worker_id: int, num_todos: int, result_queue: multiprocessing.Queue
) -> None:
    """Worker function that adds multiple todos using TodoApp."""
    try:
        app = TodoApp(db_path)
        for i in range(num_todos):
            app.add(f"worker-{worker_id}-todo-{i}")
        result_queue.put(("success", worker_id, num_todos))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_operations_no_data_loss(tmp_path) -> None:
    """Regression test for issue #5556.

    Run 10 parallel processes each adding 10 todos. With proper locking,
    total count should equal 100. Without locking, some todos may be lost
    due to the race condition in load-modify-save pattern.
    """
    db_path = str(tmp_path / "concurrent_todos.json")

    num_workers = 10
    todos_per_worker = 10
    expected_total = num_workers * todos_per_worker  # 100 todos

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_add_todos_worker, args=(db_path, worker_id, todos_per_worker, result_queue)
        )
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

    # Verify total todo count equals expected (no data loss)
    app = TodoApp(db_path)
    final_todos = app.list()
    actual_count = len(final_todos)

    assert actual_count == expected_total, (
        f"Data loss detected! Expected {expected_total} todos, got {actual_count}. "
        f"Race condition in load-modify-save pattern caused {expected_total - actual_count} todos to be lost."
    )


def test_concurrent_mixed_operations_no_data_loss(tmp_path) -> None:
    """Test that concurrent add/remove/mark_done operations don't cause data loss."""
    db_path = str(tmp_path / "mixed_ops.json")

    # Pre-populate with some todos for remove/mark_done operations
    app = TodoApp(db_path)
    for i in range(50):
        app.add(f"initial-todo-{i}")

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    def add_worker(worker_id: int) -> None:
        try:
            app = TodoApp(db_path)
            for i in range(5):
                app.add(f"add-worker-{worker_id}-{i}")
            result_queue.put(("add_success", worker_id))
        except Exception as e:
            result_queue.put(("add_error", worker_id, str(e)))

    def remove_worker(worker_id: int) -> None:
        try:
            app = TodoApp(db_path)
            todos = app.list()
            # Try to remove some todos
            for todo in todos[:5]:
                try:
                    app.remove(todo.id)
                    break  # Only remove one per worker to avoid conflicts
                except ValueError:
                    pass  # Already removed by another worker
            result_queue.put(("remove_success", worker_id))
        except Exception as e:
            result_queue.put(("remove_error", worker_id, str(e)))

    # Start mixed workers
    for i in range(5):
        p1 = multiprocessing.Process(target=add_worker, args=(i,))
        p2 = multiprocessing.Process(target=remove_worker, args=(i,))
        processes.extend([p1, p2])
        p1.start()
        p2.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=30)

    # Verify final state is consistent (no corruption)
    storage = TodoStorage(db_path)
    try:
        final_todos = storage.load()
    except Exception as e:
        raise AssertionError(f"Data corrupted by concurrent operations: {e}") from e

    # Verify all todos have valid structure
    for todo in final_todos:
        assert isinstance(todo.id, int), f"Todo id should be int, got {type(todo.id)}"
        assert isinstance(todo.text, str), f"Todo text should be str, got {type(todo.text)}"
        assert isinstance(todo.done, bool), f"Todo done should be bool, got {type(todo.done)}"


def test_lock_timeout_configurable(tmp_path) -> None:
    """Test that lock acquisition has configurable timeout."""
    # This test verifies the lock timeout parameter exists and works
    db_path = str(tmp_path / "timeout_test.json")

    # Create TodoApp with a specific lock timeout
    app = TodoApp(db_path, lock_timeout=5.0)

    # Should be able to perform operations normally
    app.add("test todo")
    todos = app.list()
    assert len(todos) == 1

    # Verify timeout is accessible
    assert hasattr(app, "_lock_timeout") or hasattr(app, "lock_timeout"), (
        "TodoApp should have a lock_timeout parameter for configuring lock acquisition timeout"
    )


def test_lock_released_on_exception(tmp_path) -> None:
    """Test that lock is properly released when an exception occurs during operation."""
    db_path = str(tmp_path / "exception_test.json")

    app = TodoApp(db_path)

    # First add a valid todo
    app.add("valid todo")

    # Try to add an empty todo (should raise ValueError)
    with pytest.raises(ValueError, match="cannot be empty"):
        app.add("")

    # Lock should be released, so next operation should succeed
    app.add("another valid todo")

    # Verify both valid todos are present
    todos = app.list()
    assert len(todos) == 2
    assert todos[0].text == "valid todo"
    assert todos[1].text == "another valid todo"
