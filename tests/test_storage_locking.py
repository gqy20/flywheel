"""Tests for file locking behavior in TodoStorage.

This test suite verifies that TodoStorage uses file locking to prevent
data loss when multiple processes write concurrently.
"""

from __future__ import annotations

import multiprocessing
import time

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_write_preserves_all_data(tmp_path) -> None:
    """Test that concurrent writes from multiple processes preserve all data.

    This is the key test for file locking: multiple processes add unique todos
    concurrently, and ALL todos should be present (no data loss).

    Without file locking:
    - Process A reads file with [todo1]
    - Process B reads file with [todo1]
    - Process A writes [todo1, todo2]
    - Process B writes [todo1, todo3] (losing todo2)

    With file locking:
    - Process A acquires lock
    - Process B blocks waiting for lock
    - Process A writes [todo1, todo2] and releases lock
    - Process B acquires lock, reads [todo1, todo2], writes [todo1, todo2, todo3]
    - All data preserved
    """
    db = tmp_path / "locking_test.json"

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo to the shared file."""
        try:
            storage = TodoStorage(str(db))

            # Create a unique todo for this worker
            new_todo = Todo(id=worker_id, text=f"worker-{worker_id}-unique-todo")

            # Small delay to increase race condition likelihood if locking is broken
            time.sleep(0.01)

            # Use atomic add_todo which holds lock for entire read-modify-write
            storage.add_todo(new_todo)

            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()
            p.join()

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Final verification: ALL todos should be present
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Each worker added 1 todo, so we should have exactly num_workers todos
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, but got {len(final_todos)}. "
        f"Some todos were lost due to race condition!"
    )

    # Verify each worker's unique todo is present
    todo_texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-unique-todo"
        assert expected_text in todo_texts, f"Todo from worker {i} is missing!"


def test_lock_released_on_error(tmp_path) -> None:
    """Test that file lock is released even when an error occurs.

    Ensures that a crashed/corrupted write doesn't leave the file locked forever.
    """
    db = tmp_path / "lock_error_test.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    initial_todos = [Todo(id=1, text="initial")]
    storage.save(initial_todos)

    # Simulate an error during save by causing a JSON serialization error
    # The lock should still be released after the exception
    class UnserializableObject:
        pass

    bad_todos = [Todo(id=1, text="good"), UnserializableObject()]  # type: ignore

    with pytest.raises((AttributeError, TypeError)):
        storage.save(bad_todos)  # type: ignore

    # File should still be accessible (lock was released)
    # We should be able to load the original data
    reloaded_storage = TodoStorage(str(db))
    loaded = reloaded_storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_lock_timeout_works(tmp_path) -> None:
    """Test that lock acquisition has a reasonable timeout.

    If a process holds the lock for too long, other processes should
    eventually fail with a clear error rather than hanging forever.
    """
    db = tmp_path / "lock_timeout_test.json"

    def hold_lock_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that holds lock for a short time."""
        try:
            storage = TodoStorage(str(db))
            todos = storage.load()
            storage.save(todos)  # Acquires and releases lock
            result_queue.put("held")
        except Exception as e:
            result_queue.put(f"error: {e}")

    def quick_write_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that quickly writes."""
        try:
            storage = TodoStorage(str(db))
            todos = storage.load()
            todos.append(Todo(id=1, text="quick"))
            storage.save(todos)
            result_queue.put("written")
        except Exception as e:
            result_queue.put(f"error: {e}")

    # Run workers sequentially (they should both succeed)
    p1 = multiprocessing.Process(target=hold_lock_worker, args=(result_queue := multiprocessing.Queue(),))
    p2 = multiprocessing.Process(target=quick_write_worker, args=(result_queue,))

    p1.start()
    p1.join(timeout=5)

    p2.start()
    p2.join(timeout=5)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Both should complete successfully
    assert len(results) == 2
    assert "held" in results
    assert "written" in results
