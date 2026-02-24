"""Regression test for issue #5556: Race condition in TodoApp operations.

This test suite verifies that TodoApp operations (add, mark_done, mark_undone, remove)
are protected against race conditions when multiple processes access the same storage.

The issue is that load-modify-save pattern is not atomic - between load and save,
another process could modify the file, causing data loss.

The fix uses file-based locking (filelock library) to protect the critical section.
"""

from __future__ import annotations

import multiprocessing
import tempfile
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_without_locking(tmp_path) -> None:
    """RED test: Multiple processes adding todos should not lose data.

    This test will FAIL before the fix and PASS after the fix is implemented.
    Each of 10 processes adds 100 todos, and we should end up with exactly 1000 todos.
    """
    db = tmp_path / "concurrent_add.json"

    def add_worker(worker_id: int, count: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds todos and reports success."""
        try:
            app = TodoApp(db_path=str(db))
            for i in range(count):
                app.add(f"worker-{worker_id}-todo-{i}")
            result_queue.put(("success", worker_id, count))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run 10 workers each adding 100 todos = 1000 expected todos
    num_workers = 10
    todos_per_worker = 100
    expected_total = num_workers * todos_per_worker
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, todos_per_worker, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=60)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Critical assertion: we should have ALL 1000 todos
    # Before the fix, this will fail due to race condition data loss
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    actual_count = len(final_todos)

    assert actual_count == expected_total, (
        f"DATA LOSS DETECTED: Expected {expected_total} todos, got {actual_count}. "
        f"Lost {expected_total - actual_count} todos due to race condition. "
        f"This is the bug described in issue #5556."
    )


def test_concurrent_mixed_operations_without_locking(tmp_path) -> None:
    """RED test: Mixed concurrent operations should not corrupt data.

    Multiple processes performing different operations (add, mark_done, remove)
    should not corrupt the storage or cause unexpected errors.
    """
    db = tmp_path / "concurrent_mixed.json"

    # Pre-populate with some todos
    app = TodoApp(db_path=str(db))
    for i in range(50):
        app.add(f"initial-todo-{i}")

    def add_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that adds todos."""
        try:
            app = TodoApp(db_path=str(db))
            for i in range(20):
                app.add(f"add-worker-todo-{i}")
            result_queue.put(("success", "add"))
        except Exception as e:
            result_queue.put(("error", "add", str(e)))

    def mark_done_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that marks todos as done."""
        try:
            app = TodoApp(db_path=str(db))
            for _ in range(20):
                todos = app.list()
                for todo in todos:
                    if not todo.done:
                        app.mark_done(todo.id)
                        break
                time.sleep(0.001)  # Small delay to increase interleaving
            result_queue.put(("success", "mark_done"))
        except Exception as e:
            result_queue.put(("error", "mark_done", str(e)))

    def remove_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that removes todos."""
        try:
            app = TodoApp(db_path=str(db))
            for _ in range(10):
                todos = app.list()
                if todos:
                    # Remove the first done todo if any, otherwise first pending
                    done_todos = [t for t in todos if t.done]
                    if done_todos:
                        app.remove(done_todos[0].id)
                    else:
                        app.remove(todos[0].id)
                time.sleep(0.002)  # Small delay to increase interleaving
            result_queue.put(("success", "remove"))
        except Exception as e:
            result_queue.put(("error", "remove", str(e)))

    # Run workers concurrently
    processes = []
    result_queue = multiprocessing.Queue()

    # 2 add workers, 2 mark_done workers, 2 remove workers
    for _ in range(2):
        p = multiprocessing.Process(target=add_worker, args=(result_queue,))
        processes.append(p)
        p.start()

    for _ in range(2):
        p = multiprocessing.Process(target=mark_done_worker, args=(result_queue,))
        processes.append(p)
        p.start()

    for _ in range(2):
        p = multiprocessing.Process(target=remove_worker, args=(result_queue,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=60)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]

    # Should have no unexpected errors (ValueError for "not found" is expected sometimes)
    unexpected_errors = [
        e for e in errors
        if "not found" not in str(e[2])
    ]
    assert len(unexpected_errors) == 0, f"Unexpected errors: {unexpected_errors}"

    # Final state should be valid
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All todos should be valid
    for todo in final_todos:
        assert isinstance(todo.id, int)
        assert isinstance(todo.text, str)
        assert isinstance(todo.done, bool)


def test_lock_timeout_is_configurable(tmp_path) -> None:
    """Test that lock acquisition has configurable timeout.

    This verifies the fix allows timeout configuration as per acceptance criteria.
    """
    db = tmp_path / "timeout_test.json"
    storage = TodoStorage(str(db))

    # After fix, TodoStorage should support a lock_timeout parameter
    # Default should be reasonable (e.g., 30 seconds)
    # This test verifies the parameter is accepted

    # Create a storage with custom timeout
    storage_with_timeout = TodoStorage(str(db), lock_timeout=5.0)

    # Should be able to perform operations
    storage_with_timeout.save([Todo(id=1, text="test")])
    todos = storage_with_timeout.load()
    assert len(todos) == 1


def test_lock_released_on_exception(tmp_path) -> None:
    """Test that lock is properly released when an exception occurs.

    This prevents deadlock scenarios.
    """
    db = tmp_path / "exception_test.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Simulate an exception during operation
    # After fix, the lock should still be released
    from unittest.mock import patch
    import json

    with patch.object(json, "dumps", side_effect=ValueError("Simulated error")):
        with pytest.raises(ValueError, match="Simulated error"):
            storage.save([Todo(id=2, text="should fail")])

    # Lock should be released - we should be able to do another operation
    storage.save([Todo(id=3, text="after error")])
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "after error"
