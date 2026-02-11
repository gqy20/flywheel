"""Tests for file locking mechanism in TodoStorage - Issue #2844.

This test suite verifies that TodoStorage uses file locking to prevent
concurrent write conflicts and ensure data integrity across multiple processes.
"""

from __future__ import annotations

import json
import multiprocessing
import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_without_lock_allows_overwrite(tmp_path) -> None:
    """Test that without file locking, concurrent saves have last-writer-wins behavior.

    This test documents the CURRENT (undesirable) behavior where data loss occurs.
    After implementing file locks, this behavior should change.
    """
    db = tmp_path / "no_lock.json"
    storage = TodoStorage(str(db))

    # First process writes 3 todos
    todos1 = [
        Todo(id=1, text="process-1-todo-1"),
        Todo(id=2, text="process-1-todo-2"),
        Todo(id=3, text="process-1-todo-3"),
    ]
    storage.save(todos1)

    # Second process writes different todos (simulates concurrent access)
    todos2 = [Todo(id=1, text="process-2-todo-1")]
    storage.save(todos2)

    # Without proper locking, last writer wins and we lose data
    loaded = storage.load()
    assert len(loaded) == 1, "Without locking, last writer wins - data loss occurs"


def worker_save_and_read(
    worker_id: int,
    db_path: str,
    barrier: multiprocessing.Barrier,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker that saves todos and attempts to read them back.

    Uses a barrier to synchronize concurrent access and increase race likelihood.
    """
    try:
        storage = TodoStorage(db_path)

        # Each worker creates unique todos using worker_id
        todos = [
            Todo(id=1, text=f"worker-{worker_id}-todo-1"),
            Todo(id=2, text=f"worker-{worker_id}-todo-2"),
        ]

        # Wait for all workers to be ready, then race to save
        barrier.wait()

        start_time = time.time()
        storage.save(todos)
        save_time = time.time() - start_time

        # Try to read back immediately
        loaded = storage.load()

        result_queue.put(("success", worker_id, len(loaded), save_time))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_save_with_locking_serializes_access(tmp_path) -> None:
    """Test that file locking serializes concurrent save operations.

    Multiple workers should all complete successfully, and the final
    state should be valid JSON (no corruption). With proper locking,
    operations are serialized preventing data corruption.
    """
    db = tmp_path / "concurrent_locked.json"

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()
    barrier = multiprocessing.Barrier(num_workers)

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=worker_save_and_read,
            args=(i, str(db), barrier, result_queue),
        )
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Final state must be valid JSON
    storage = TodoStorage(str(db))
    try:
        final_todos = storage.load()
    except (json.JSONDecodeError, ValueError) as e:
        raise AssertionError(
            f"File was corrupted despite locking. Got error: {e}"
        ) from e

    # Verify data integrity
    assert isinstance(final_todos, list)
    for todo in final_todos:
        assert hasattr(todo, "id")
        assert hasattr(todo, "text")


def worker_read_during_write(
    worker_id: int,
    db_path: str,
    write_done: multiprocessing.Event,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker that attempts to read while another process writes."""
    try:
        storage = TodoStorage(db_path)

        if worker_id == 0:
            # Writer process
            todos = [
                Todo(id=1, text="write-todo-1"),
                Todo(id=2, text="write-todo-2"),
            ]
            storage.save(todos)
            write_done.set()
        else:
            # Reader processes - wait for writer to start
            # With proper locking, readers should block or get consistent data
            time.sleep(0.01)  # Small delay to let writer start
            loaded = storage.load()
            result_queue.put(("read", worker_id, len(loaded)))

        result_queue.put(("success", worker_id, None))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_read_during_write_gets_consistent_data(tmp_path) -> None:
    """Test that reads during write operations get consistent data.

    With file locking:
    - Readers should wait for exclusive write locks to release
    - Readers should never see partially written/corrupted data
    """
    db = tmp_path / "read_during_write.json"

    # Pre-populate with data
    storage = TodoStorage(str(db))
    initial_todos = [Todo(id=1, text="initial-todo")]
    storage.save(initial_todos)

    num_workers = 3
    processes = []
    result_queue = multiprocessing.Queue()
    write_done = multiprocessing.Event()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=worker_read_during_write,
            args=(i, str(db), write_done, result_queue),
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Check all workers succeeded
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final file is valid
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    assert isinstance(final_todos, list)
    assert len(final_todos) >= 1  # Should have at least some data


def test_storage_has_file_lock_mechanism(tmp_path) -> None:
    """Test that TodoStorage implements file locking mechanism.

    This is a RED test that fails until file locking is implemented.
    After implementation, the storage should have a lock attribute
    and use filelock (or similar) for concurrent access protection.
    """
    db = tmp_path / "lock_test.json"
    storage = TodoStorage(str(db))

    # After implementing file locks, TodoStorage should expose
    # the lock mechanism. This test fails until implemented.
    assert hasattr(storage, "_lock"), "TodoStorage should have a _lock attribute for file locking"

    # The lock should use a lock file in the same directory
    # with a predictable naming convention
    if storage._lock is not None:
        lock_file = getattr(storage._lock, "lock_file", None)
        assert lock_file is not None, "Lock should have a lock_file attribute"


def test_concurrent_writes_prevent_data_loss(tmp_path) -> None:
    """RED test: Verify that concurrent writes do NOT lose data with file locking.

    This test will FAIL until proper file locking is implemented.
    Without locking, one writer's data will overwrite another's.
    With locking, we should preserve data from all operations.
    """
    import multiprocessing

    db = tmp_path / "no_data_loss.json"
    num_workers = 3

    def writer_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Each worker adds a unique todo to the file."""
        try:
            storage = TodoStorage(str(db))
            # Load existing todos first
            existing = storage.load()

            # Add a new unique todo
            new_todo = Todo(id=worker_id + 100, text=f"unique-worker-{worker_id}")
            updated = existing + [new_todo]

            # Save
            storage.save(updated)

            # Verify it was saved
            reloaded = storage.load()
            found = any(t.id == worker_id + 100 for t in reloaded)
            result_queue.put(("success", worker_id, found))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    processes = []
    result_queue = multiprocessing.Queue()

    # Initialize with one todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    # Run concurrent writers
    for i in range(num_workers):
        p = multiprocessing.Process(target=writer_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify all writes were preserved
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Without file locking, some todos will be lost due to last-writer-wins
    # With file locking, all todos should be present
    # Workers add todos with IDs: worker 0 -> 100, worker 1 -> 101, worker 2 -> 102
    expected_ids = {1, 100, 101, 102}  # initial + workers 0,1,2 + 100
    actual_ids = {t.id for t in final_todos}

    # This assertion fails without proper file locking!
    assert actual_ids == expected_ids, (
        f"Data loss detected! Expected todos with IDs {expected_ids}, "
        f"but got {actual_ids}. This indicates lack of proper file locking."
    )
