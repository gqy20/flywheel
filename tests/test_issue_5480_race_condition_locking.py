"""Tests for issue #5480: Race condition detection and file locking.

This test suite verifies that TodoStorage provides protection against
concurrent writes causing last-writer-wins data loss.

The fix implements file locking (fcntl.flock on Unix, msvcrt.locking on Windows)
to ensure that load+save operations are atomic from the perspective of data integrity.
"""

from __future__ import annotations

import multiprocessing

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_load_modify_save_no_data_loss(tmp_path) -> None:
    """Test that concurrent load-modify-save sequences with locking prevent data loss.

    This test verifies that using the locked() context manager for load-modify-save
    sequences prevents the last-writer-wins data loss scenario.

    Scenario:
    1. Process A and B both want to add a todo
    2. Using locking ensures they serialize their operations
    3. Both todos should be present in the final file

    This tests the fix for issue #5480.
    """
    db = tmp_path / "todos.json"

    # Initial state: 1 todo
    initial_storage = TodoStorage(str(db))
    initial_todos = [Todo(id=1, text="initial")]
    initial_storage.save(initial_todos)

    # Two separate storage instances representing two processes
    storage_a = TodoStorage(str(db))
    storage_b = TodoStorage(str(db))

    # Process A: uses locked() context manager for atomic load-modify-save
    with storage_a.locked():
        todos_a = storage_a.load()
        todos_a.append(Todo(id=2, text="from process A"))
        storage_a.save(todos_a)

    # Process B: uses locked() context manager for atomic load-modify-save
    # Even though it starts after A releases the lock, it will load the
    # current state (including A's changes) before adding its own
    with storage_b.locked():
        todos_b = storage_b.load()
        todos_b.append(Todo(id=3, text="from process B"))
        storage_b.save(todos_b)

    # Final verification: all 3 todos should be present (no data loss)
    final_storage = TodoStorage(str(db))
    final_todos = final_storage.load()

    assert len(final_todos) == 3, (
        f"Expected 3 todos (initial + A's + B's), got {len(final_todos)}. "
        f"Last-writer-wins data loss occurred."
    )

    # Verify all expected todos are present
    todo_texts = {t.text for t in final_todos}
    expected_texts = {"initial", "from process A", "from process B"}
    assert todo_texts == expected_texts, f"Missing todos. Expected {expected_texts}, got {todo_texts}"


def test_file_lock_is_released_on_exception(tmp_path) -> None:
    """Test that file lock is released even if save fails.

    This ensures we don't leave the file permanently locked if an
    exception occurs during the save operation.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Initial state
    storage.save([Todo(id=1, text="initial")])

    # First, acquire lock and have an operation fail
    try:
        with storage.locked():
            # Simulate an error during save
            raise OSError("Simulated error")
    except OSError:
        pass  # Expected

    # Lock should be released now, so we should be able to acquire it again
    # and successfully save
    with storage.locked():
        storage.save([Todo(id=1, text="updated")])

    # Verify the save worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"


def test_sequential_operations_with_locking_work(tmp_path) -> None:
    """Test that sequential operations with locking work correctly.

    This ensures that the locking mechanism doesn't break normal usage.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Sequential operations should all succeed
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")])

    loaded = storage.load()
    assert len(loaded) == 3


def test_multiprocess_concurrent_save_with_locking(tmp_path) -> None:
    """Test that multiple processes using locking don't lose data.

    Each process should:
    1. Acquire lock
    2. Load current todos
    3. Add its own todo
    4. Save
    5. Release lock

    All todos from all processes should be present in the final file.
    """
    db = tmp_path / "concurrent.json"

    # Initial state
    initial_storage = TodoStorage(str(db))
    initial_storage.save([Todo(id=0, text="initial")])

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using proper locking."""
        try:
            storage = TodoStorage(str(db))
            with storage.locked():
                # Load current state
                todos = storage.load()
                # Add our todo with a unique ID (worker_id + 1 to avoid 0)
                new_todo = Todo(id=worker_id + 1, text=f"from-worker-{worker_id}")
                todos.append(new_todo)
                # Save
                storage.save(todos)
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

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Final verification: all todos should be present
    final_storage = TodoStorage(str(db))
    final_todos = final_storage.load()

    # Should have: initial + 5 worker todos = 6 total
    assert len(final_todos) == num_workers + 1, (
        f"Expected {num_workers + 1} todos (1 initial + {num_workers} workers), "
        f"got {len(final_todos)}. Last-writer-wins data loss occurred."
    )

    # Verify all worker todos are present
    todo_ids = {t.id for t in final_todos}
    expected_ids = {0, 1, 2, 3, 4, 5}  # Initial (0) + workers (1-5)
    assert todo_ids == expected_ids, f"Missing todo IDs. Expected {expected_ids}, got {todo_ids}"


def test_lock_context_manager_provides_exclusive_access(tmp_path) -> None:
    """Test that the lock context manager provides exclusive access.

    When one storage instance has the lock, another should not be able
    to acquire it (unless using non-blocking mode).
    """
    db = tmp_path / "todos.json"
    storage1 = TodoStorage(str(db))
    storage2 = TodoStorage(str(db))

    # Initialize
    storage1.save([Todo(id=1, text="initial")])

    # First lock holder
    with storage1.locked():
        # Second storage should not be able to acquire lock (non-blocking)
        acquired = storage2.try_lock()
        assert acquired is False, "Second storage should not acquire lock while first holds it"

    # After first releases, second should be able to acquire
    acquired = storage2.try_lock()
    assert acquired is True, "Second storage should acquire lock after first releases"
    storage2.unlock()
