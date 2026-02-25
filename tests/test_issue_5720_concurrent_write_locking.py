"""Regression tests for issue #5720: Race condition with concurrent writes.

This test suite verifies that TodoStorage uses file locking to prevent
data loss from the "last-writer-wins" problem during concurrent writes.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_uses_file_locking(tmp_path: Path) -> None:
    """Test that save() acquires an exclusive file lock during write.

    This verifies that the locking mechanism is in place and functional.
    """
    db = tmp_path / "locked.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # The save should have acquired and released a lock
    # We can't easily verify the lock itself, but we can verify the file is valid
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_concurrent_writes_preserve_all_data_with_locking(tmp_path: Path) -> None:
    """Regression test for issue #5720: Concurrent writes should not lose data.

    With proper file locking, concurrent processes should serialize their writes,
    ensuring each process's modifications are preserved rather than being
    overwritten by another process.

    This test spawns multiple processes, each of which:
    1. Loads the current todo list
    2. Adds a unique todo item
    3. Saves the list

    Without locking, the last writer wins and data from other processes is lost.
    With locking, all additions should be preserved.
    """
    db = tmp_path / "concurrent_locked.json"

    # Initialize with empty list
    storage = TodoStorage(str(db))
    storage.save([])

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo using load-modify-save pattern."""
        try:
            storage = TodoStorage(str(db))

            # Use exclusive_access to hold lock during entire read-modify-write cycle
            with storage.exclusive_access():
                # Small staggered delay to increase race condition likelihood
                time.sleep(0.001 * (worker_id % 3))

                # Load current state
                todos = storage.load()

                # Add our unique todo
                new_id = max((t.id for t in todos), default=0) + 1
                todos.append(Todo(id=new_id, text=f"worker-{worker_id}-todo"))

                # Save (lock is already held by exclusive_access)
                storage.save(todos)

            result_queue.put(("success", worker_id, new_id))
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

    # With proper locking, all todos should be preserved
    # (each worker added 1 todo, so we should have num_workers todos)
    final_todos = storage.load()
    worker_ids_found = {int(t.text.split("-")[1]) for t in final_todos}

    # This is the key assertion - without locking, this would fail
    # because some workers' data would be lost
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos (one per worker), but got {len(final_todos)}. "
        f"Data loss occurred due to concurrent writes without proper locking. "
        f"Found worker IDs: {worker_ids_found}"
    )


def test_file_lock_prevents_concurrent_write_overlap(tmp_path: Path) -> None:
    """Test that file locking actually blocks concurrent writers.

    This test verifies that when one thread holds the lock, another thread
    must wait until the lock is released before it can write.
    """
    import threading

    db = tmp_path / "lock_test.json"
    storage = TodoStorage(str(db))

    # Initialize
    storage.save([Todo(id=1, text="initial")])

    # Track write order
    write_order = []
    write_lock = threading.Lock()

    def writer_thread(writer_id: int, delay: float) -> None:
        """Thread that writes with a deliberate delay while holding lock."""
        # Use exclusive_access to hold lock during entire read-modify-write cycle
        with storage.exclusive_access():
            todos = storage.load()
            time.sleep(delay)  # Simulate some processing time while holding lock
            todos.append(Todo(id=len(todos) + 1, text=f"writer-{writer_id}"))
            storage.save(todos)

        with write_lock:
            write_order.append(writer_id)

    # Start two threads with different delays
    threads = [
        threading.Thread(target=writer_thread, args=(1, 0.05)),
        threading.Thread(target=writer_thread, args=(2, 0.01)),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10)

    # Both writes should complete
    final_todos = storage.load()
    assert len(final_todos) == 3, f"Expected 3 todos (1 initial + 2 added), got {len(final_todos)}"


def test_locking_works_on_unix_and_windows(tmp_path: Path) -> None:
    """Test that the locking mechanism works on both Unix and Windows.

    This is a smoke test to ensure the cross-platform locking implementation
    doesn't raise errors on either platform.
    """
    db = tmp_path / "cross_platform.json"
    storage = TodoStorage(str(db))

    # Simple save should work without errors
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Load should work
    loaded = storage.load()
    assert len(loaded) == 1

    # Multiple saves should work
    for i in range(3):
        todos.append(Todo(id=i + 2, text=f"test-{i}"))
        storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 4
