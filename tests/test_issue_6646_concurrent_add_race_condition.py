"""Regression test for issue #6646: Race condition in add() causes data loss.

This test verifies that concurrent add() operations do not result in data loss
and each todo is assigned a unique ID.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_no_data_loss(tmp_path: Path) -> None:
    """Test that concurrent add() operations don't lose data.

    Verifies:
    - All todos added concurrently should appear in final storage
    - Each todo should be assigned a unique ID
    """
    db = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db))

    num_threads = 5
    results: list[Exception | None] = [None] * num_threads
    threads = []

    def add_todo(thread_id: int) -> None:
        try:
            todo = app.add(f"thread-{thread_id}-todo")
            results[thread_id] = None  # Success
        except Exception as e:
            results[thread_id] = e

    # Create and start all threads simultaneously
    for i in range(num_threads):
        t = threading.Thread(target=add_todo, args=(i,))
        threads.append(t)

    # Start all threads as close together as possible
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # Verify no exceptions occurred
    exceptions = [r for r in results if r is not None]
    assert len(exceptions) == 0, f"Threads encountered exceptions: {exceptions}"

    # Load final todos and verify all are present
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All 5 todos should be present (no data loss)
    assert len(final_todos) == num_threads, (
        f"Expected {num_threads} todos, but got {len(final_todos)}. "
        f"Data loss occurred due to race condition."
    )

    # Verify all todos have unique IDs
    ids = [todo.id for todo in final_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    # Verify all thread todos are present
    texts = {todo.text for todo in final_todos}
    for i in range(num_threads):
        expected_text = f"thread-{i}-todo"
        assert expected_text in texts, f"Missing todo from thread {i}"


def test_concurrent_add_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() assigns unique IDs.

    This is a more targeted test focusing specifically on ID uniqueness.
    """
    db = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db))

    num_threads = 10
    barrier = threading.Barrier(num_threads)
    collected_ids: list[int] = []
    lock = threading.Lock()

    def add_todo_and_collect_id(thread_id: int) -> None:
        # Synchronize all threads to start at exactly the same time
        barrier.wait(timeout=10)
        todo = app.add(f"sync-thread-{thread_id}")
        with lock:
            collected_ids.append(todo.id)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=add_todo_and_collect_id, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    # All IDs should be unique
    assert len(collected_ids) == num_threads, (
        f"Expected {num_threads} IDs, got {len(collected_ids)}"
    )
    assert len(set(collected_ids)) == num_threads, (
        f"Duplicate IDs detected: {collected_ids}"
    )


def test_sequential_add_works_correctly(tmp_path: Path) -> None:
    """Baseline test: sequential add() should work without issues."""
    db = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db))

    for i in range(5):
        todo = app.add(f"sequential-{i}")
        assert todo.id == i + 1

    storage = TodoStorage(str(db))
    todos = storage.load()
    assert len(todos) == 5
