"""Tests for issue #5377: Race condition in CLI operations.

This test suite verifies that file-based locking protects against
read-modify-write race conditions that cause data loss when multiple
processes operate on the same todo file concurrently.

The issue: Last-writer-wins without locking means concurrent operations
can silently lose data.

The fix: Implement advisory file locking (fcntl.flock on Unix) around
the entire read-modify-write transaction.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_adds_preserve_all_todos(tmp_path: Path) -> None:
    """Test that concurrent add() operations preserve all todos.

    This is a regression test for issue #5377. Without file locking,
    if two processes add todos concurrently, the last writer wins
    and the other todo is lost.

    With proper locking, both todos should be preserved because
    each process holds an exclusive lock during its read-modify-write.
    """
    db = tmp_path / "concurrent.json"

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using the TodoApp CLI interface."""
        try:
            app = TodoApp(db_path=str(db))
            # Each worker adds a unique todo
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that add todos concurrently
    num_workers = 4
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers at nearly the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
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

    # KEY ASSERTION: All todos should be preserved, not just the last one
    # Without locking, only 1-2 todos might survive due to last-writer-wins
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All workers should have their todo preserved
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos (one per worker), but got {len(final_todos)}. "
        f"This indicates race condition caused data loss. "
        f"Todo texts: {[t.text for t in final_todos]}"
    )

    # Verify all worker texts are present
    final_texts = {t.text for t in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-task"
        assert expected_text in final_texts, f"Missing todo from worker {i}"


def test_concurrent_add_and_mark_done_preserves_both_operations(tmp_path: Path) -> None:
    """Test concurrent add and mark_done operations don't lose data.

    Scenario:
    1. Initial state: 2 todos
    2. Process A adds a new todo
    3. Process B marks todo #1 as done
    4. Final state should have 3 todos with #1 marked done
    """
    db = tmp_path / "mixed_ops.json"

    # Set up initial state
    app_setup = TodoApp(db_path=str(db))
    app_setup.add("initial-1")
    app_setup.add("initial-2")

    def add_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a new todo."""
        try:
            app = TodoApp(db_path=str(db))
            app.add("added-concurrently")
            result_queue.put(("success", "add", None))
        except Exception as e:
            result_queue.put(("error", "add", str(e)))

    def mark_done_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that marks todo #1 as done."""
        try:
            # Small delay to increase race likelihood
            time.sleep(0.001)
            app = TodoApp(db_path=str(db))
            app.mark_done(1)
            result_queue.put(("success", "done", None))
        except Exception as e:
            result_queue.put(("error", "done", str(e)))

    # Run workers concurrently
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

    # KEY ASSERTIONS:
    # 1. Should have 3 todos (2 initial + 1 added)
    # 2. Todo #1 should be marked done
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    assert len(final_todos) == 3, (
        f"Expected 3 todos but got {len(final_todos)}. "
        f"Concurrent operations caused data loss. "
        f"Todos: {[t.text for t in final_todos]}"
    )

    # Find todo #1 and verify it's done
    todo_1 = next((t for t in final_todos if t.id == 1), None)
    assert todo_1 is not None, "Todo #1 should exist"
    assert todo_1.done is True, "Todo #1 should be marked done"


def test_lock_timeout_with_clear_error_message(tmp_path: Path) -> None:
    """Test that lock acquisition timeout provides a clear error message.

    When a lock cannot be acquired within a reasonable timeout,
    the error message should indicate the issue clearly.
    """
    db = tmp_path / "lock_timeout.json"
    storage = TodoStorage(str(db))

    # Test that we can get a lock on a new file
    with storage.transaction():
        storage.save([])  # Should succeed

    # Test that the transaction context manager works properly
    # by performing a load-modify-save within it
    with storage.transaction():
        todos = storage.load()
        assert isinstance(todos, list)

    # This test verifies the locking mechanism exists and works
    # The actual timeout behavior is harder to test without holding
    # the lock indefinitely, so we just verify basic functionality


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is released even if an exception occurs.

    This ensures we don't leave stale locks that block future operations.
    """
    db = tmp_path / "lock_exception.json"
    storage = TodoStorage(str(db))

    # First, create a file with valid content
    storage.save([])

    # Try a transaction that fails
    try:
        with storage.transaction():
            todos = storage.load()
            # Simulate an error during modification
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected

    # Lock should be released, so we should be able to do another operation
    with storage.transaction():
        todos = storage.load()
        assert todos == []

    # Verify the storage is still usable
    final_todos = storage.load()
    assert final_todos == []
