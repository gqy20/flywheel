"""Regression test for issue #5165: Race condition causing duplicate IDs.

This test verifies that concurrent add operations do not result in duplicate IDs
and that no data is lost due to last-writer-wins overwrites.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the assigned ID.

    Args:
        worker_id: Unique identifier for this worker
        db_path: Path to the shared database file
        result_queue: Queue to report results back to main process
    """
    try:
        app = TodoApp(db_path=db_path)
        # Add a unique todo with worker_id in the text
        todo = app.add(f"worker-{worker_id}-task")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_no_duplicate_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations do not produce duplicate IDs.

    Verification criteria (from issue #5165):
    - Two concurrent add operations should not result in duplicate IDs
    - All todos should have unique IDs even under concurrent access
    - Data should not be lost due to last-writer-wins overwrites
    """
    db_path = str(tmp_path / "concurrent_todos.json")

    # Run 5 concurrent processes each adding a todo to the same file
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers at roughly the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Extract IDs that were assigned
    assigned_ids = [r[2] for r in successes]

    # Verify all IDs are unique (no duplicates)
    assert len(assigned_ids) == len(set(assigned_ids)), (
        f"Duplicate IDs detected! Got IDs: {sorted(assigned_ids)}. "
        f"This indicates a race condition in ID generation."
    )

    # Load the final state and verify no data loss
    storage = TodoStorage(db_path)
    loaded_todos = storage.load()

    # All 5 todos should be present (no data loss)
    assert len(loaded_todos) == num_workers, (
        f"Data loss detected! Expected {num_workers} todos, got {len(loaded_todos)}. "
        f"This indicates last-writer-wins overwrites."
    )

    # All loaded IDs should be unique
    loaded_ids = [t.id for t in loaded_todos]
    assert len(loaded_ids) == len(set(loaded_ids)), (
        f"Duplicate IDs in final data! Got IDs: {sorted(loaded_ids)}"
    )

    # All worker texts should be present
    loaded_texts = {t.text for t in loaded_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-task"
        assert expected_text in loaded_texts, f"Missing todo from worker {i}: {expected_text}"


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Test that concurrent additions preserve all todos, not just the last writer's.

    This is a more specific test for the 'data loss' aspect of the race condition.
    """
    db_path = str(tmp_path / "concurrent_todos2.json")

    # Pre-populate with some todos
    app = TodoApp(db_path=db_path)
    app.add("initial-todo-1")
    app.add("initial-todo-2")

    # Run concurrent adds
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i + 100, db_path, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results and check for errors
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Load final state
    storage = TodoStorage(db_path)
    loaded_todos = storage.load()

    # Should have 2 initial + 5 new = 7 todos
    assert len(loaded_todos) == 7, (
        f"Data loss detected! Expected 7 todos (2 initial + 5 new), got {len(loaded_todos)}. "
        f"Todos: {[t.text for t in loaded_todos]}"
    )

    # All IDs should be unique
    loaded_ids = [t.id for t in loaded_todos]
    assert len(loaded_ids) == len(set(loaded_ids)), (
        f"Duplicate IDs in final data! Got IDs: {sorted(loaded_ids)}"
    )


def test_sequential_adds_no_race_condition(tmp_path: Path) -> None:
    """Baseline test: sequential adds should work without any race condition issues."""
    db_path = str(tmp_path / "sequential_todos.json")
    app = TodoApp(db_path=db_path)

    # Add todos sequentially
    ids = []
    for i in range(5):
        todo = app.add(f"sequential-task-{i}")
        ids.append(todo.id)

    # All IDs should be unique and sequential
    assert ids == [1, 2, 3, 4, 5], f"Expected sequential IDs 1-5, got {ids}"

    # Load and verify
    storage = TodoStorage(db_path)
    loaded_todos = storage.load()
    assert len(loaded_todos) == 5

    loaded_ids = sorted([t.id for t in loaded_todos])
    assert loaded_ids == [1, 2, 3, 4, 5]
