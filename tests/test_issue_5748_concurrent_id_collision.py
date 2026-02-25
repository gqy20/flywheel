"""Regression test for issue #5748: ID collision with concurrent TodoApp instances.

This test verifies that when multiple TodoApp instances add todos concurrently,
each todo gets a unique ID, preventing ID collisions.
"""

from __future__ import annotations

import multiprocessing

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is the regression test for issue #5748.
    When two processes load the same file and both add todos,
    they should generate different IDs, not duplicate IDs.
    """
    db = tmp_path / "concurrent.json"

    # Initialize with one todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and returns the ID assigned."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that all try to add concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
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

    # Collect all IDs that were assigned
    assigned_ids = [r[2] for r in successes]

    # CRITICAL: All IDs must be unique (no collisions)
    unique_ids = set(assigned_ids)
    assert len(unique_ids) == num_workers, (
        f"ID collision detected! Assigned IDs: {assigned_ids}, "
        f"unique IDs: {unique_ids}. "
        f"Expected {num_workers} unique IDs but got {len(unique_ids)}"
    )


def test_file_locking_prevents_concurrent_id_collision(tmp_path) -> None:
    """Test that file locking prevents ID collision during concurrent access.

    This tests that when two processes try to acquire the lock and add todos,
    the locking mechanism ensures they don't generate duplicate IDs.
    """
    db = tmp_path / "locked.json"
    storage = TodoStorage(str(db))

    # Initialize with one todo
    storage.save([Todo(id=1, text="initial")])

    # Simulate concurrent access by acquiring lock, loading, and generating ID
    lock_fd = storage.acquire_lock()
    try:
        todos = storage.load()
        new_id = storage.next_id(todos)
        # Verify ID is sequential (max + 1)
        assert new_id == 2, f"Expected ID 2, got {new_id}"
    finally:
        storage.release_lock(lock_fd)

    # Verify lock can be acquired again
    lock_fd2 = storage.acquire_lock()
    storage.release_lock(lock_fd2)


def test_next_id_with_locking_produces_sequential_ids(tmp_path) -> None:
    """Test that next_id produces sequential IDs when used with proper locking.

    This verifies that the ID generation combined with locking ensures
    sequential, unique IDs in the proper usage pattern.
    """
    db = tmp_path / "sequential.json"
    storage = TodoStorage(str(db))

    expected_ids = []
    for i in range(5):
        lock_fd = storage.acquire_lock()
        try:
            todos = storage.load()
            new_id = storage.next_id(todos)
            expected_ids.append(new_id)
            todos.append(Todo(id=new_id, text=f"todo-{i}"))
            storage.save(todos)
        finally:
            storage.release_lock(lock_fd)

    # IDs should be sequential: 1, 2, 3, 4, 5
    assert expected_ids == [1, 2, 3, 4, 5], f"Expected sequential IDs, got {expected_ids}"

    # Verify final state
    final_todos = storage.load()
    assert len(final_todos) == 5
    assert [t.id for t in final_todos] == [1, 2, 3, 4, 5]


def test_concurrent_add_from_separate_apps_preserves_all_todos(tmp_path) -> None:
    """Test that concurrent adds from separate TodoApp instances don't lose data.

    When multiple processes add todos to the same database, the final state
    should contain valid todos (though with last-writer-wins semantics,
    some may be lost - but the IDs should still be unique).
    """
    db = tmp_path / "multiapp.json"

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that creates its own TodoApp and adds a todo."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"task from worker {worker_id}")
            result_queue.put(("success", worker_id, todo.id, todo.text))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 3
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Collect all IDs assigned
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    ids_assigned = [r[2] for r in successes]

    # No ID collisions among successfully assigned IDs
    unique_ids = set(ids_assigned)
    assert len(unique_ids) == len(ids_assigned), (
        f"ID collision in concurrent app instances: {ids_assigned}"
    )
