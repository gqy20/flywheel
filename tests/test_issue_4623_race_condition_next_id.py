"""Regression test for issue #4623: TOCTOU race condition in next_id and save.

This test verifies that concurrent add operations produce unique IDs.
The issue was that between load() and save(), multiple threads could
read the same state and compute the same next_id, causing duplicate IDs.

Fix: Add threading.Lock to TodoStorage to make load->next_id->save atomic.
"""

from __future__ import annotations

import threading
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_produces_unique_ids_threading(tmp_path: Path) -> None:
    """Test that concurrent TodoApp.add() calls produce unique IDs.

    This is a regression test for issue #4623. Without proper locking,
    multiple threads calling add() concurrently could get duplicate IDs
    because:
    1. Thread A loads todos []
    2. Thread B loads todos []
    3. Thread A computes next_id([]) = 1
    4. Thread B computes next_id([]) = 1  <-- DUPLICATE!
    5. Thread A saves [Todo(id=1)]
    6. Thread B saves [Todo(id=1)]  <-- Lost update + duplicate ID
    """
    db_path = tmp_path / "test.json"
    app = TodoApp(db_path=str(db_path))

    num_threads = 10
    results: list[int] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def add_todo(worker_id: int) -> None:
        try:
            todo = app.add(f"task-{worker_id}")
            with lock:
                results.append(todo.id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=add_todo, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    # Check for errors
    assert len(errors) == 0, f"Errors during concurrent add: {errors}"

    # All IDs should be unique
    assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
    assert len(set(results)) == num_threads, f"Duplicate IDs found: {results}"

    # Verify final storage has unique IDs
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]
    assert len(set(final_ids)) == len(final_ids), f"Duplicate IDs in storage: {final_ids}"


def test_concurrent_add_from_separate_apps_produces_unique_ids(tmp_path: Path) -> None:
    """Test concurrent adds from separate TodoApp instances.

    This simulates multiple processes/clients adding todos concurrently.
    Each TodoApp instance has its own TodoStorage but shares the same file.
    """
    db_path = tmp_path / "test.json"
    num_threads = 8
    results: list[int] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def add_todo(worker_id: int) -> None:
        try:
            # Each thread creates its own TodoApp instance
            app = TodoApp(db_path=str(db_path))
            todo = app.add(f"task-{worker_id}")
            with lock:
                results.append(todo.id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=add_todo, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    # Check for errors
    assert len(errors) == 0, f"Errors during concurrent add: {errors}"

    # All IDs should be unique
    assert len(results) == num_threads
    assert len(set(results)) == num_threads, f"Duplicate IDs found: {results}"


def test_high_concurrency_add_all_ids_unique(tmp_path: Path) -> None:
    """Stress test: 20 concurrent adds should all produce unique IDs."""
    db_path = tmp_path / "stress.json"
    app = TodoApp(db_path=str(db_path))

    num_threads = 20
    results: list[int] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def add_todo(worker_id: int) -> None:
        try:
            todo = app.add(f"stress-task-{worker_id}")
            with lock:
                results.append(todo.id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=add_todo, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert len(errors) == 0, f"Errors during stress test: {errors}"
    assert len(results) == num_threads
    assert len(set(results)) == num_threads, f"Duplicate IDs in stress test: {results}"
