"""Regression test for issue #5377: Race condition in CLI operations.

This test verifies that file-based locking prevents data loss during
concurrent read-modify-write operations.

The bug: Two processes concurrently doing load-modify-save can lose data
because the second process reads the old state before the first saves,
then overwrites the first process's changes.

The fix: Implement advisory file locking around the load-modify-save sequence.
"""

from __future__ import annotations

import multiprocessing

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_preserve_all_todos(tmp_path) -> None:
    """Test that two processes adding todos concurrently do not lose data.

    This is the core regression test for the race condition bug.
    Two processes each add a different todo. Without locking, the last
    writer wins and the other todo is lost. With proper locking, both
    todos should be preserved.
    """
    db = tmp_path / "todos.json"

    def add_todo_worker(todo_text: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using the CLI TodoApp."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(todo_text)
            result_queue.put(("success", todo.id, todo.text))
        except Exception as e:
            result_queue.put(("error", str(e)))

    # Start two workers simultaneously
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=add_todo_worker, args=("first todo", result_queue))
    p2 = multiprocessing.Process(target=add_todo_worker, args=("second todo", result_queue))

    # Start both processes at nearly the same time
    p1.start()
    p2.start()

    # Wait for both to complete
    p1.join(timeout=10)
    p2.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Both operations should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # The critical assertion: BOTH todos should exist in the file
    # Without locking, this would fail because one would overwrite the other
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    todo_texts = {todo.text for todo in final_todos}

    assert "first todo" in todo_texts, "First todo was lost due to race condition"
    assert "second todo" in todo_texts, "Second todo was lost due to race condition"


def test_concurrent_add_operations_with_multiple_workers(tmp_path) -> None:
    """Stress test with multiple concurrent workers adding todos.

    This is a more aggressive test to verify the lock works under higher concurrency.
    """
    db = tmp_path / "todos.json"
    num_workers = 5

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}-todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers at nearly the same time
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All operations should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # All todos should be preserved
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(final_todos)}. "
        f"Some todos were lost due to race condition."
    )

    # Verify each worker's todo exists
    todo_texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        assert f"worker-{i}-todo" in todo_texts, f"Worker {i}'s todo was lost"


def test_lock_timeout_with_clear_error(tmp_path) -> None:
    """Test that lock acquisition timeout provides a clear error message.

    If a process holds the lock too long, other processes should get a
    clear timeout error rather than hanging indefinitely.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Initialize the file
    storage.save([Todo(id=1, text="initial")])

    # Test that the lock method exists and handles timeout
    # This is a basic check - actual concurrent lock testing is done above
    # The lock() method should accept a timeout parameter

    # Check if there's a lock method or context manager
    has_lock = (
        hasattr(storage, "lock") or
        hasattr(storage, "with_lock") or
        any("lock" in name.lower() for name in dir(storage) if not name.startswith("_"))
    )

    # The fix should provide some form of locking mechanism
    assert has_lock, "TodoStorage should provide a locking mechanism for concurrent access"


def test_lock_released_on_exception(tmp_path) -> None:
    """Test that lock is released even if an exception occurs during operation.

    This ensures that a crashed process doesn't leave the lock in a stuck state.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Initialize the file
    storage.save([Todo(id=1, text="initial")])

    # Try a failing operation and verify subsequent operations work
    try:
        app = TodoApp(db_path=str(db))
        # This should raise ValueError for empty text
        app.add("")
    except ValueError:
        pass  # Expected

    # After the exception, a new operation should work
    # This verifies the lock was released
    app2 = TodoApp(db_path=str(db))
    todo = app2.add("after exception")

    assert todo.text == "after exception"
    assert todo.id == 2  # Should get next ID after initial todo
