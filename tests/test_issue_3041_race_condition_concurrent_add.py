"""Regression tests for Issue #3041: Race condition in concurrent add operations.

The issue: CLI add operation is not atomic - concurrent adds can cause ID
collision and data loss.

Location: src/flywheel/cli.py:30 - add() method loads todos, calculates
next_id, appends, then saves - not atomic.

This test suite verifies that:
1. Concurrent add operations from multiple processes should not produce duplicate IDs
2. No data loss when two processes add todos simultaneously
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def test_concurrent_adds_produce_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations don't produce duplicate IDs.

    This is the core regression test for issue #3041.
    Multiple processes adding todos concurrently should result in:
    - All todos having unique IDs (no ID collision)
    - No data loss (all added todos are present)
    """
    db_path = str(tmp_path / "concurrent_test.json")
    num_workers = 5
    todos_per_worker = 10
    total_expected_todos = num_workers * todos_per_worker

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    def add_todos_worker(worker_id: int) -> None:
        """Worker that adds multiple todos to the shared database."""
        try:
            app = TodoApp(db_path=db_path)
            added_ids = []
            for i in range(todos_per_worker):
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                added_ids.append(todo.id)
            result_queue.put(("success", worker_id, added_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers at roughly the same time to increase race condition likelihood
    for i in range(num_workers):
        # Use multiprocessing.Process with target as function
        p = multiprocessing.Process(target=add_todos_worker, args=(i,))
        processes.append(p)

    # Start all processes nearly simultaneously
    for p in processes:
        p.start()

    # Wait for all processes to complete with timeout
    for p in processes:
        p.join(timeout=30)

    # Check that all processes finished
    unfinished = [i for i, p in enumerate(processes) if p.is_alive()]
    assert not unfinished, f"Processes {unfinished} did not complete in time"

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Separate successes and errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}"
    )

    # Collect all IDs that were assigned
    all_ids = []
    for _status, _worker_id, ids in successes:
        all_ids.extend(ids)

    # Check for duplicate IDs - this is the core assertion for issue #3041
    unique_ids = set(all_ids)
    duplicates = len(all_ids) - len(unique_ids)
    assert duplicates == 0, (
        f"Found {duplicates} duplicate IDs in {len(all_ids)} total IDs. "
        f"IDs: {sorted(all_ids)[:50]}..."
    )

    # Verify the final database state
    final_app = TodoApp(db_path=db_path)
    final_todos = final_app.list(show_all=True)

    # Count expected vs actual
    actual_count = len(final_todos)
    # Note: Due to race condition, some todos may be lost (last-writer-wins)
    # This is what we're trying to fix. The test should fail before the fix.
    # After fix, all todos should be present.

    # Get actual IDs in the final database
    final_ids = [todo.id for todo in final_todos]
    unique_final_ids = set(final_ids)

    # Core assertions for issue #3041:
    # 1. No duplicate IDs in the final database
    assert len(final_ids) == len(unique_final_ids), (
        f"Final database has {len(final_ids) - len(unique_final_ids)} "
        f"duplicate IDs: {[i for i in final_ids if final_ids.count(i) > 1]}"
    )

    # 2. All todos should be present (no data loss)
    assert actual_count == total_expected_todos, (
        f"Expected {total_expected_todos} todos in database, "
        f"but only found {actual_count}. "
        f"Some todos were lost due to race condition."
    )


def test_concurrent_adds_from_same_process(tmp_path: Path) -> None:
    """Simpler test: two TodoApp instances adding concurrently on same file.

    This tests the race condition without multiprocessing complexity.
    """
    db_path = str(tmp_path / "simple_race.json")

    # Create two app instances pointing to same file
    app1 = TodoApp(db_path=db_path)
    app2 = TodoApp(db_path=db_path)

    # Add initial todo to establish baseline
    initial = app1.add("initial todo")
    assert initial.id == 1

    # Now simulate race condition:
    # Both apps load the same state (with ID 1)
    # Both calculate next_id = 2
    # Both save, resulting in ID collision

    # Manually trigger the race by loading before add
    todos1 = app1._load()
    todos2 = app2._load()

    # Both see same state
    assert len(todos1) == 1
    assert len(todos2) == 1

    # Calculate next IDs - both will be 2
    next_id1 = app1.storage.next_id(todos1)
    next_id2 = app2.storage.next_id(todos2)
    assert next_id1 == 2
    assert next_id2 == 2

    # Add from both - this should trigger the race
    todo1 = Todo(id=next_id1, text="from app1")
    todos1.append(todo1)
    app1._save(todos1)

    # App2 still has stale data
    todo2 = Todo(id=next_id2, text="from app2")
    todos2.append(todo2)
    # This will overwrite app1's todo or cause ID collision
    app2._save(todos2)

    # Load final state
    final = app1.list(show_all=True)

    # Before fix: We expect only 2 todos (app2's save overwrote app1's)
    # After fix: Both todos should be preserved with unique IDs
    # For now, we document the race condition exists
    # The assertion below will fail after the fix is applied
    assert len(final) == 2, (
        f"Expected 2 todos (showing race condition: app2 overwrote app1), "
        f"got {len(final)}"
    )

    # Check if we have duplicate IDs (the actual bug)
    final_ids = [t.id for t in final]
    if len(final_ids) != len(set(final_ids)):
        pytest.fail(
            f"Race condition detected: duplicate IDs found: {final_ids}. "
            f"This is the bug reported in issue #3041."
        )


def test_rapid_sequential_adds_different_processes(tmp_path: Path) -> None:
    """Test rapid sequential adds from different processes.

    This tests a realistic scenario where multiple CLI invocations
    happen in quick succession.
    """
    import subprocess
    import sys

    db_path = str(tmp_path / "rapid_add.json")
    num_adds = 10

    # Run multiple add commands in rapid succession
    processes = []
    for i in range(num_adds):
        cmd = [
            sys.executable,
            "-m",
            "flywheel.cli",
            "--db",
            db_path,
            "add",
            f"rapid-todo-{i}",
        ]
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append(p)

    # Wait for all processes
    for p in processes:
        p.wait(timeout=10)

    # Load final state
    app = TodoApp(db_path=db_path)
    todos = app.list(show_all=True)

    # All todos should be present
    assert len(todos) == num_adds, (
        f"Expected {num_adds} todos, got {len(todos)}. "
        f"Some todos were lost due to race condition."
    )

    # All IDs should be unique
    ids = [t.id for t in todos]
    assert len(ids) == len(set(ids)), (
        f"Duplicate IDs found: {[i for i in ids if ids.count(i) > 1]}"
    )

    # IDs should be sequential from 1 to num_adds
    expected_ids = list(range(1, num_adds + 1))
    assert sorted(ids) == expected_ids, (
        f"Expected IDs {expected_ids}, got {sorted(ids)}"
    )
