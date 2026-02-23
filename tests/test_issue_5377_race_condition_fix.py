"""Regression test for issue #5377: Race condition in CLI operations.

This test suite verifies that file-based locking prevents data loss during
concurrent read-modify-write operations.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Test that two concurrent add operations preserve both todos.

    This is the core regression test for issue #5377. Without locking,
    two processes can read the same state, each add a todo, and one
    todo will be lost when the second process saves (last-writer-wins).

    With proper locking, both todos should be preserved.
    """
    db_path = tmp_path / "test.json"

    # Initialize with one todo
    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="initial")])

    def add_todo_worker(todo_text: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using TodoApp."""
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(todo_text)
            result_queue.put(("success", todo.id, todo.text))
        except Exception as e:
            result_queue.put(("error", str(e)))

    # Run two workers concurrently, each adding a different todo
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

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify both succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers failed: {errors}"
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # Critical assertion: both todos should be in the final file
    # Without locking, only one might survive due to last-writer-wins
    final_todos = storage.load()
    final_texts = {todo.text for todo in final_todos}

    assert "initial" in final_texts, "Initial todo was lost"
    assert "concurrent-todo-0" in final_texts, "concurrent-todo-0 was lost (race condition)"
    assert "concurrent-todo-1" in final_texts, "concurrent-todo-1 was lost (race condition)"


def test_lock_timeout_with_clear_error(tmp_path: Path) -> None:
    """Test that lock acquisition timeout produces clear error message."""
    db_path = tmp_path / "test_lock.json"
    storage = TodoStorage(str(db_path))

    # Create a locked context and verify timeout behavior
    # This test verifies that the lock mechanism is in place
    with storage.locked_operation(timeout=1.0):
        # While holding the lock, try to acquire again in a subprocess
        def try_lock_worker(result_queue: multiprocessing.Queue) -> None:
            try:
                sub_storage = TodoStorage(str(db_path))
                # Try with very short timeout - should fail
                with sub_storage.locked_operation(timeout=0.1):
                    result_queue.put(("acquired", None))
            except TimeoutError as e:
                result_queue.put(("timeout", str(e)))
            except Exception as e:
                result_queue.put(("error", str(e)))

        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        p = multiprocessing.Process(target=try_lock_worker, args=(result_queue,))
        p.start()
        p.join(timeout=10)

        result = result_queue.get()
        assert result[0] == "timeout", f"Expected timeout, got: {result}"
        assert "lock" in result[1].lower() or "timeout" in result[1].lower(), \
            f"Error message should mention lock or timeout: {result[1]}"


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is released even if an exception occurs."""
    db_path = tmp_path / "test_exception.json"
    storage = TodoStorage(str(db_path))

    # Trigger an exception while holding lock
    with pytest.raises(ValueError, match="test error"):
        with storage.locked_operation():
            raise ValueError("test error")

    # Lock should be released, we can acquire it again
    with storage.locked_operation(timeout=1.0):
        pass  # Lock acquired successfully


def test_lock_released_on_normal_exit(tmp_path: Path) -> None:
    """Test that lock is released after normal operation completion."""
    db_path = tmp_path / "test_normal.json"
    storage = TodoStorage(str(db_path))

    # Acquire and release lock normally
    with storage.locked_operation(timeout=1.0):
        storage.save([Todo(id=1, text="test")])

    # Should be able to acquire lock again immediately
    with storage.locked_operation(timeout=1.0):
        todos = storage.load()
        assert len(todos) == 1
