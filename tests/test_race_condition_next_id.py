"""Regression test for issue #4623: Race condition between next_id and save.

This test verifies that concurrent add operations produce unique IDs.
The bug was a TOCTOU (Time Of Check To Time Of Use) race condition:
1. Thread A loads todos, calculates next_id=1
2. Thread B loads todos, calculates next_id=1 (same as A)
3. Thread A saves with id=1
4. Thread B saves with id=1 (duplicate!)

Fix: Use threading.Lock to protect the load -> next_id -> save sequence.
"""

from __future__ import annotations

import threading
from pathlib import Path

from flywheel.cli import TodoApp


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs (issue #4623)."""
    db_path = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db_path))

    num_threads = 10
    results: list[int] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def add_todo(thread_id: int) -> None:
        try:
            todo = app.add(f"Task from thread {thread_id}")
            with lock:
                results.append(todo.id)
        except Exception as e:
            with lock:
                errors.append(e)

    # Create and start all threads
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=add_todo, args=(i,))
        threads.append(t)

    # Start all threads as close together as possible
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # Check for errors
    assert len(errors) == 0, f"Threads encountered errors: {errors}"

    # All IDs should be unique
    assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"
    assert len(set(results)) == num_threads, (
        f"Duplicate IDs detected! IDs: {sorted(results)}. "
        f"This indicates a race condition in next_id/save."
    )


def test_concurrent_add_ids_match_file_content(tmp_path: Path) -> None:
    """Test that IDs in file match what was returned from add operations."""
    db_path = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db_path))

    num_threads = 5
    returned_ids: list[int] = []
    lock = threading.Lock()

    def add_todo(thread_id: int) -> None:
        todo = app.add(f"Task {thread_id}")
        with lock:
            returned_ids.append(todo.id)

    threads = [threading.Thread(target=add_todo, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Load file and check IDs
    from flywheel.storage import TodoStorage

    storage = TodoStorage(str(db_path))
    stored_ids = [todo.id for todo in storage.load()]

    # All returned IDs should be in the file
    for rid in returned_ids:
        assert rid in stored_ids, f"Returned ID {rid} not found in file: {stored_ids}"

    # File IDs should be unique
    assert len(stored_ids) == len(set(stored_ids)), (
        f"Duplicate IDs in file: {stored_ids}"
    )


def test_high_concurrency_add_operations(tmp_path: Path) -> None:
    """Test high concurrency scenario with 20+ concurrent add operations."""
    db_path = tmp_path / "todo.json"
    app = TodoApp(db_path=str(db_path))

    num_threads = 25
    results: list[int] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def add_todo(thread_id: int) -> None:
        try:
            todo = app.add(f"High concurrency task {thread_id}")
            with lock:
                results.append(todo.id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=add_todo, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(errors) == 0, f"Errors in high concurrency test: {errors}"
    assert len(results) == num_threads
    assert len(set(results)) == num_threads, (
        f"Duplicate IDs in high concurrency: {sorted(results)}"
    )
