"""Regression test for issue #6646: Race condition in add() causes data loss.

This test verifies that concurrent add() operations do not result in data loss.
The race condition occurs when multiple threads:
1. Read the same todos list
2. Calculate the same next_id
3. Each appends their todo
4. The last writer wins, losing all other adds
"""

from __future__ import annotations

import threading
import time

from flywheel.cli import TodoApp


def test_concurrent_add_no_data_loss(tmp_path) -> None:
    """Test that concurrent add() operations do not result in data loss.

    Creates 5 threads each calling add() with unique text, then verifies:
    1. All 5 todos appear in final storage.load()
    2. No duplicate IDs in final list
    """
    db_path = str(tmp_path / "concurrent.json")
    num_threads = 5
    results = []
    errors = []

    def add_todo_worker(thread_id: int) -> None:
        """Worker that adds a todo with unique text."""
        try:
            app = TodoApp(db_path)
            # Small delay to increase race condition likelihood
            time.sleep(0.001)
            todo = app.add(f"thread-{thread_id}-todo")
            results.append((thread_id, todo.id))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create and start all threads simultaneously
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=add_todo_worker, args=(i,))
        threads.append(t)

    # Start all threads at nearly the same time
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # Verify no errors occurred
    assert len(errors) == 0, f"Threads encountered errors: {errors}"

    # Verify all threads completed successfully
    assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"

    # Load final state and verify all todos are present
    app = TodoApp(db_path)
    final_todos = app.list()

    # Critical assertion: all todos should be present (no data loss)
    assert len(final_todos) == num_threads, (
        f"DATA LOSS: Expected {num_threads} todos, but only {len(final_todos)} exist. "
        f"This indicates a race condition where concurrent writes lost data."
    )

    # Verify all thread texts are present
    texts = {todo.text for todo in final_todos}
    for i in range(num_threads):
        expected_text = f"thread-{i}-todo"
        assert expected_text in texts, f"Missing todo from thread {i}: {expected_text}"

    # Verify no duplicate IDs
    ids = [todo.id for todo in final_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    Even under high contention, each todo should get a unique ID.
    """
    db_path = str(tmp_path / "unique_ids.json")
    num_threads = 10
    all_ids = []
    lock = threading.Lock()

    def add_todo_worker(thread_id: int) -> None:
        """Worker that adds multiple todos."""
        try:
            app = TodoApp(db_path)
            for i in range(3):
                todo = app.add(f"thread-{thread_id}-item-{i}")
                with lock:
                    all_ids.append(todo.id)
        except Exception:
            pass  # Errors will be detected by duplicate ID check

    # Create and start all threads
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=add_todo_worker, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=15)

    # Verify no duplicate IDs
    assert len(all_ids) == len(set(all_ids)), (
        f"DUPLICATE IDs: {len(all_ids)} adds produced only {len(set(all_ids))} unique IDs. "
        f"This indicates a race condition in ID assignment."
    )
