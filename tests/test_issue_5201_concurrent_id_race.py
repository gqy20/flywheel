"""Tests for race condition in next_id() between load and save.

This test suite verifies that concurrent processes performing add() operations
do not generate duplicate IDs.

Issue: #5201
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5201: Race condition in next_id().

    Tests that multiple processes calling add() concurrently produce
    unique todo IDs, not duplicates.

    The race condition occurs when:
    1. Process A loads todos with max_id=1, computes next_id=2
    2. Process B loads todos with max_id=1, computes next_id=2 (same!)
    3. Both processes save, resulting in duplicate ID=2
    """
    db = tmp_path / "concurrent_ids.json"

    # Initialize with a starting todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and returns the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            # Each worker adds a unique todo
            todo = app.add(f"worker-{worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    # Use enough workers to increase likelihood of race condition
    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Stagger start times slightly to maximize overlap in critical section
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()
        # Small delay to create overlapping windows but not sequential
        time.sleep(0.002)

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # THE KEY ASSERTION: All IDs must be unique
    # This is the regression test - before fix, duplicate IDs would be generated
    ids = [r[2] for r in successes]
    unique_ids = set(ids)

    assert len(unique_ids) == len(ids), (
        f"Duplicate IDs detected! Got {len(ids)} todos but only {len(unique_ids)} unique IDs. "
        f"IDs: {sorted(ids)}, duplicates: {[id for id in ids if ids.count(id) > 1]}"
    )

    # Verify final state has no duplicate IDs
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]
    assert len(set(final_ids)) == len(final_ids), (
        f"Final storage has duplicate IDs: {sorted(final_ids)}"
    )


def test_race_condition_deterministic_reproduction(tmp_path: Path) -> None:
    """Deterministic test that exposes the race condition in next_id().

    This test uses mocking to force the race condition scenario:
    1. Both processes load the same state
    2. Both compute next_id before either saves
    3. This guarantees duplicate IDs without proper locking
    """
    import json

    db = tmp_path / "race_test.json"

    # Initialize with starting todo
    db.write_text(
        json.dumps(
            [{"id": 1, "text": "initial", "done": False, "created_at": "", "updated_at": ""}]
        )
    )

    # Create two TodoApp instances that will simulate concurrent access
    app1 = TodoApp(db_path=str(db))
    app2 = TodoApp(db_path=str(db))

    # Capture the original save method
    original_save = TodoStorage.save
    save_barrier_hit = [False]  # Use list for mutability in closure
    saved_ids: list[int] = []

    def patched_save(self: TodoStorage, todos: list[Todo]) -> None:
        """Patched save that creates a barrier to force race condition."""
        # Record the ID being saved
        new_todo = todos[-1]  # The newly added todo
        saved_ids.append(new_todo.id)

        if not save_barrier_hit[0]:
            # First save: wait to let second process also compute ID
            save_barrier_hit[0] = True
            time.sleep(0.1)  # Give second process time to load and compute
        original_save(self, todos)

    with patch.object(TodoStorage, "save", patched_save):
        # Simulate two concurrent add operations
        # Both will load the same state, compute next_id=2, and save
        import threading

        results: list[int] = []

        def add_with_app(app: TodoApp, text: str) -> None:
            todo = app.add(text)
            results.append(todo.id)

        t1 = threading.Thread(target=add_with_app, args=(app1, "task from app1"))
        t2 = threading.Thread(target=add_with_app, args=(app2, "task from app2"))

        t1.start()
        time.sleep(0.01)  # Let t1 load and start computing
        t2.start()

        t1.join(timeout=5)
        t2.join(timeout=5)

    # This is the key assertion: both threads should have unique IDs
    # Without the fix, both will have ID=2 (duplicate)
    assert len(set(results)) == len(results), (
        f"Race condition produced duplicate IDs: {results}. "
        f"Both processes loaded the same state and computed the same next_id."
    )


def test_concurrent_add_with_file_locking_produces_unique_ids(tmp_path: Path) -> None:
    """Test that with proper locking, concurrent adds are safe.

    This test verifies that when file locking is properly implemented,
    concurrent add operations produce unique IDs.
    """
    db = tmp_path / "locked_concurrent_ids.json"

    # Initialize with a starting todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def add_worker_with_delay(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo with intentional race window."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers with tight timing to maximize race condition exposure
    num_workers = 15
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker_with_delay, args=(i, result_queue))
        processes.append(p)
        p.start()
        # Very small delay to create overlap
        time.sleep(0.001)

    for p in processes:
        p.join(timeout=20)

    # Collect and verify
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Allow for some failures due to lock contention (but not duplicates)
    assert len(successes) >= num_workers - 2, (
        f"Too many failures: {len(errors)} errors, {len(successes)} successes. Errors: {errors}"
    )

    # All successful adds must have unique IDs
    ids = [r[2] for r in successes]
    assert len(set(ids)) == len(ids), f"Duplicate IDs in successful adds: {sorted(ids)}"


def test_sequential_add_produces_unique_ids(tmp_path: Path) -> None:
    """Baseline test: sequential adds should always produce unique IDs."""
    db = tmp_path / "sequential_ids.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos sequentially
    ids = []
    for i in range(20):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # All IDs should be unique
    assert len(set(ids)) == len(ids), f"Sequential adds produced duplicate IDs: {ids}"

    # IDs should be sequential starting from 1
    expected_ids = list(range(1, 21))
    assert ids == expected_ids, f"Expected IDs {expected_ids}, got {ids}"
