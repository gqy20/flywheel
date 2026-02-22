"""Regression test for issue #5165: Race condition with duplicate IDs.

This test verifies that concurrent add operations do not result in duplicate IDs
and that data is not lost due to last-writer-wins semantics.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_todo_worker(db_path: str, text: str, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds a single todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(text)
        result_queue.put(("success", todo.id, text))
    except Exception as e:
        result_queue.put(("error", str(e), text))


def test_concurrent_add_operations_no_duplicate_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is a regression test for issue #5165.

    Given: An empty todo database
    When: Multiple processes concurrently add todos
    Then: All todos should have unique IDs and no data should be lost
    """
    db_path = str(tmp_path / "concurrent.json")

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers as close together as possible to maximize race condition
    for i in range(num_workers):
        text = f"concurrent-todo-{i}"
        p = multiprocessing.Process(target=_add_todo_worker, args=(db_path, text, result_queue))
        processes.append(p)

    # Start all at once
    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Check no errors occurred
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # All workers should have succeeded
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Load final state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Get all IDs from the final state
    final_ids = [todo.id for todo in final_todos]

    # Critical assertion: All IDs must be unique (no duplicates)
    unique_ids = set(final_ids)
    assert len(unique_ids) == len(final_ids), (
        f"Duplicate IDs found! IDs: {final_ids}. "
        f"This indicates a race condition in ID generation."
    )

    # Critical assertion: All todos should be present (no data loss)
    assert len(final_todos) == num_workers, (
        f"Data loss detected! Expected {num_workers} todos, but only {len(final_todos)} remain. "
        f"This indicates last-writer-wins data loss."
    )

    # Verify all worker texts are present in final state
    final_texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        expected_text = f"concurrent-todo-{i}"
        assert expected_text in final_texts, (
            f"Todo '{expected_text}' was lost due to race condition. "
            f"Remaining texts: {final_texts}"
        )


def test_concurrent_add_produces_sequential_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent adds produce sequential IDs without gaps or duplicates.

    Given: An empty todo database
    When: Multiple processes concurrently add todos
    Then: IDs should be sequential (1, 2, 3, ...) with no duplicates
    """
    db_path = str(tmp_path / "sequential.json")

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        text = f"seq-todo-{i}"
        p = multiprocessing.Process(target=_add_todo_worker, args=(db_path, text, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Errors: {errors}"

    # Load final state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # All IDs should be present
    final_ids = sorted([todo.id for todo in final_todos])

    # IDs should be sequential starting from 1
    expected_ids = list(range(1, num_workers + 1))
    assert final_ids == expected_ids, (
        f"IDs should be sequential. Expected {expected_ids}, got {final_ids}"
    )
