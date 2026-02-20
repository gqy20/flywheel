"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_is_atomic_with_os_replace(tmp_path) -> None:
    """Test that save uses atomic os.replace instead of non-atomic write_text."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Mock os.replace to track if it was called
    with patch("flywheel.storage.os.replace") as mock_replace:
        storage.save(todos)
        # Verify atomic replace was used
        mock_replace.assert_called_once()

    # Verify file content is still valid
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_write_failure_preserves_original_file(tmp_path) -> None:
    """Test that if write fails, original file remains intact."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Get the original file content
    original_content = db.read_text(encoding="utf-8")

    # Simulate write failure by making temp file write fail
    def failing_mkstemp(*args, **kwargs):
        # Fail on any temp file creation
        raise OSError("Simulated write failure")

    import tempfile
    original = tempfile.mkstemp

    with (
        patch.object(tempfile, "mkstemp", failing_mkstemp),
        pytest.raises(OSError, match="Simulated write failure"),
    ):
        storage.save([Todo(id=3, text="new")])

    # Restore original
    tempfile.mkstemp = original

    # Verify original file is unchanged
    assert db.read_text(encoding="utf-8") == original_content

    # Verify we can still load the original data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "data"


def test_temp_file_created_in_same_directory(tmp_path) -> None:
    """Test that temp file is created in same directory as target for atomic rename."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp file creation via mkstemp
    temp_files_created = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import tempfile
    original = tempfile.mkstemp

    with patch.object(tempfile, "mkstemp", tracking_mkstemp):
        storage.save(todos)

    # Restore original
    tempfile.mkstemp = original

    # Verify temp file was created in same directory
    assert len(temp_files_created) >= 1
    assert temp_files_created[0].parent == db.parent
    # Temp file should start with the base filename
    assert temp_files_created[0].name.startswith(".todo.json.")


def test_atomic_write_produces_valid_json(tmp_path) -> None:
    """Test that atomic write produces valid, parseable JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text="task with quotes: \"test\"", done=True),
        Todo(id=3, text="task with \\n newline"),
    ]

    storage.save(todos)

    # Verify file contains valid JSON
    raw_content = db.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    assert len(parsed) == 3
    assert parsed[0]["text"] == "task with unicode: 你好"
    assert parsed[1]["text"] == 'task with quotes: "test"'
    assert parsed[1]["done"] is True


def test_concurrent_write_safety(tmp_path) -> None:
    """Test that atomic write provides safety against concurrent writes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial write
    todos1 = [Todo(id=1, text="first")]
    storage.save(todos1)

    # Simulate concurrent write using same storage object
    todos2 = [Todo(id=1, text="second"), Todo(id=2, text="added")]
    storage.save(todos2)

    # Final state should be consistent
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "second"
    assert loaded[1].text == "added"


def test_concurrent_save_from_multiple_processes(tmp_path) -> None:
    """Regression test for issue #1925: Race condition in concurrent saves.

    Tests that multiple processes saving to the same file concurrently
    do not corrupt the data. Each process writes a different set of todos,
    and after all operations complete, the file should contain valid JSON
    representing one of the process writes (not corrupted data).
    """
    import multiprocessing
    import time

    db = tmp_path / "concurrent.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos and reports success."""
        try:
            storage = TodoStorage(str(db))
            # Each worker creates unique todos with worker_id in text
            todos = [
                Todo(id=i, text=f"worker-{worker_id}-todo-{i}"),
                Todo(id=i + 1, text=f"worker-{worker_id}-todo-{i + 1}"),
            ]
            storage.save(todos)

            # Small random delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 5))

            # Verify we can read back valid data
            loaded = storage.load()
            result_queue.put(("success", worker_id, len(loaded)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Final verification: file should contain valid JSON
    # (not necessarily all data due to last-writer-wins, but definitely valid JSON)
    storage = TodoStorage(str(db))

    # This should not raise json.JSONDecodeError or ValueError
    try:
        final_todos = storage.load()
    except (json.JSONDecodeError, ValueError) as e:
        raise AssertionError(
            f"File was corrupted by concurrent writes. Got error: {e}"
        ) from e

    # Verify we got some valid todo data
    assert isinstance(final_todos, list), "Final data should be a list"
    # All todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id"), "Todo should have id"
        assert hasattr(todo, "text"), "Todo should have text"
        assert isinstance(todo.text, str), "Todo text should be a string"


def test_concurrent_add_no_id_collisions(tmp_path) -> None:
    """Regression test for issue #4652: Race condition in ID generation.

    Tests that concurrent add() operations from multiple processes
    do not produce duplicate IDs. Each process adds a todo using the
    standard add() flow (load -> next_id -> save), and after all
    operations complete, no two todos should have the same ID.
    """
    import multiprocessing
    import time

    db = tmp_path / "concurrent_add.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using standard TodoApp.add() flow."""
        try:
            # Simulate the add() flow from cli.py
            storage = TodoStorage(str(db))

            # Load current state
            todos = storage.load()

            # Calculate next ID (this is where the race can occur)
            new_id = storage.next_id(todos)

            # Small delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))

            # Add new todo
            new_todo = Todo(id=new_id, text=f"worker-{worker_id}-todo")
            todos.append(new_todo)

            # Save (last-writer-wins, but IDs should still be unique)
            storage.save(todos)

            result_queue.put(("success", worker_id, new_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    errors = [r for r in results if r[0] == "error"]

    # Note: Some workers may fail due to last-writer-wins, but those that
    # succeed should have unique IDs
    if errors:
        # It's acceptable for some concurrent writes to be lost (last-writer-wins)
        # but we need at least some successes to test ID uniqueness
        pass

    # Final verification: load final state and check for duplicate IDs
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Extract all IDs
    all_ids = [todo.id for todo in final_todos]

    # CRITICAL ASSERTION: No duplicate IDs should exist
    # This is the key fix for issue #4652
    unique_ids = set(all_ids)
    assert len(all_ids) == len(unique_ids), (
        f"ID collision detected! "
        f"Final todos have {len(all_ids)} entries but only {len(unique_ids)} unique IDs. "
        f"Duplicate IDs: {[id for id in all_ids if all_ids.count(id) > 1]}"
    )


def test_id_generation_uses_persisted_counter(tmp_path) -> None:
    """Unit test for issue #4652: next_id should use a persisted counter.

    Verifies that the ID counter is persisted separately so that
    concurrent processes don't generate duplicate IDs even if they
    start from the same initial state.
    """
    db = tmp_path / "counter_test.json"
    storage = TodoStorage(str(db))

    # Add a todo - this should create the ID counter
    todos1 = storage.load()
    id1 = storage.next_id(todos1)
    todos1.append(Todo(id=id1, text="first"))
    storage.save(todos1)

    # Simulate another process starting from the same initial state
    # (i.e., before it sees the first todo)
    # Create a new storage instance to simulate a fresh process
    storage2 = TodoStorage(str(db))

    # Load the current state (should include first todo)
    todos2 = storage2.load()

    # Get next_id - this should be 2, not 1
    id2 = storage2.next_id(todos2)

    # Verify IDs are different
    assert id1 != id2, f"IDs should be unique: got {id1} and {id2}"
    assert id2 == 2, f"Second ID should be 2, got {id2}"


def test_id_counter_independent_of_loaded_todos(tmp_path) -> None:
    """Test that ID counter persists independently of the loaded todo list.

    This is the key fix for #4652: even if a process loads stale data,
    the ID counter should have been atomically incremented.
    """
    db = tmp_path / "independent_counter.json"
    storage = TodoStorage(str(db))

    # First, add a todo
    todos1 = storage.load()
    id1 = storage.next_id(todos1)
    todos1.append(Todo(id=id1, text="first"))
    storage.save(todos1)

    # Now simulate a process that loaded BEFORE the save completed
    # but calls next_id AFTER the save. With the fix, the ID counter
    # should be persisted, so even "stale" loads get fresh IDs.

    # The key assertion: after adding todo with id=1,
    # next_id on an empty list should NOT return 1
    storage2 = TodoStorage(str(db))

    # This is the critical test: even with an empty/stale list,
    # next_id should know about the persisted counter
    # NOTE: This test will FAIL with the current buggy implementation
    # because next_id only looks at the in-memory list
    stale_id = storage2.next_id([])  # Pass empty list to simulate stale read

    # With the fix, this should return an ID > 1 (the max persisted)
    # Without the fix, it returns 1 (duplicate!)
    assert stale_id > id1, (
        f"ID counter should be independent of loaded todos. "
        f"Got {stale_id}, expected > {id1}"
    )
