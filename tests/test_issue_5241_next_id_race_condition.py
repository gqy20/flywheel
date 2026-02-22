"""Regression test for issue #5241: next_id() race condition in concurrent scenarios.

This test verifies that concurrent calls to TodoApp.add() produce unique IDs.
The bug was that next_id() calculated IDs based on the current list state
without any locking, leading to duplicate IDs in concurrent scenarios.

Root cause:
- cli.py:30 - add() executes load -> next_id -> save non-atomically
- storage.py:127 - next_id() computes max+1 without lock protection
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _concurrent_add_worker(
    db_path: str, text: str, result_queue: multiprocessing.Queue
) -> None:
    """Worker process that adds a todo and returns the assigned ID."""
    try:
        app = TodoApp(db_path)
        todo = app.add(text)
        result_queue.put(("success", todo.id))
    except Exception as e:
        result_queue.put(("error", str(e)))


def test_concurrent_add_produces_unique_ids() -> None:
    """Verify that two concurrent add() operations produce different IDs.

    This is the core regression test for issue #5241.
    Two processes simultaneously calling add() must not get the same ID.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "todos.json")

        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # Start two processes simultaneously
        processes = []
        for i in range(2):
            p = multiprocessing.Process(
                target=_concurrent_add_worker,
                args=(db_path, f"concurrent-todo-{i}", result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for both to complete
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Both operations should succeed
        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

        # IDs must be unique
        ids = [r[1] for r in successes]
        assert len(ids) == len(set(ids)), (
            f"Race condition detected: duplicate IDs {ids}. "
            f"All concurrent adds must produce unique IDs."
        )


def test_five_concurrent_adds_produce_unique_ids() -> None:
    """Verify that 5 concurrent add() operations produce 5 different IDs.

    Additional verification that the fix handles multiple concurrent writers.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "todos.json")

        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # Start 5 processes simultaneously
        processes = []
        for i in range(5):
            p = multiprocessing.Process(
                target=_concurrent_add_worker,
                args=(db_path, f"multi-concurrent-{i}", result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for all to complete
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # All operations should succeed
        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"

        # IDs must be unique
        ids = [r[1] for r in successes]
        assert len(ids) == len(set(ids)), (
            f"Race condition detected: duplicate IDs {ids}. "
            f"All 5 concurrent adds must produce unique IDs."
        )

        # Verify final storage has all todos with unique IDs
        storage = TodoStorage(db_path)
        final_todos = storage.load()
        final_ids = [t.id for t in final_todos]
        # May have fewer todos due to last-writer-wins, but all IDs should be unique
        assert len(final_ids) == len(set(final_ids)), (
            f"Final storage has duplicate IDs: {final_ids}"
        )


def test_concurrent_add_json_file_remains_valid() -> None:
    """Verify that concurrent writes don't corrupt the JSON file.

    After concurrent adds, the storage file must be valid JSON.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "todos.json")

        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # Start multiple processes
        processes = []
        for i in range(3):
            p = multiprocessing.Process(
                target=_concurrent_add_worker,
                args=(db_path, f"integrity-test-{i}", result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for all to complete
        for p in processes:
            p.join(timeout=10)

        # Verify file is valid JSON and can be loaded
        storage = TodoStorage(db_path)
        todos = storage.load()  # Should not raise

        # All loaded todos should have valid structure
        for todo in todos:
            assert isinstance(todo.id, int), f"Todo id should be int, got {type(todo.id)}"
            assert isinstance(todo.text, str), f"Todo text should be str, got {type(todo.text)}"
