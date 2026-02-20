"""Regression tests for issue #4790: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition between exists() check and mkdir() call in _ensure_parent_directory.
Two concurrent processes calling save() simultaneously could raise FileExistsError
when one process creates the directory after another's exists() check returns False.

Fix: Use exist_ok=True in mkdir() to handle the race condition gracefully.

These tests verify the fix handles concurrent directory creation properly.
"""

from __future__ import annotations

import concurrent.futures
import threading

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_save_no_toctou_race_condition(tmp_path) -> None:
    """Issue #4790: Two concurrent processes calling save() should not raise FileExistsError.

    Before fix: Race window between exists() check (line 43) and mkdir() call (line 45)
    allows concurrent process to create directory, causing FileExistsError.

    After fix: exist_ok=True handles the race condition gracefully.
    """
    # Create a path to a non-existent directory
    db_path = tmp_path / "nested" / "subdir" / "todo.json"

    # Verify the parent directory does not exist initially
    assert not db_path.parent.exists()

    storage1 = TodoStorage(str(db_path))
    storage2 = TodoStorage(str(db_path))

    todos1 = [Todo(id=1, text="Task from process 1", done=False)]
    todos2 = [Todo(id=2, text="Task from process 2", done=False)]

    # Use barrier to maximize race condition probability
    barrier = threading.Barrier(2)
    errors = []

    def save_with_barrier(storage: TodoStorage, todos: list[Todo]) -> None:
        barrier.wait()  # Synchronize both threads
        try:
            storage.save(todos)
        except Exception as e:
            errors.append(e)

    # Run concurrent saves using threads for precise synchronization
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(save_with_barrier, storage1, todos1)
        future2 = executor.submit(save_with_barrier, storage2, todos2)
        future1.result()
        future2.result()

    # No FileExistsError or other exceptions should have occurred
    assert len(errors) == 0, f"Concurrent save raised errors: {errors}"


def test_multiple_concurrent_saves_no_race(tmp_path) -> None:
    """Issue #4790: Multiple concurrent saves to same non-existent parent should all succeed."""
    db_path = tmp_path / "deep" / "nested" / "path" / "todo.json"

    assert not db_path.parent.exists()

    num_threads = 10
    storages = [TodoStorage(str(db_path)) for _ in range(num_threads)]
    errors = []
    barrier = threading.Barrier(num_threads)

    def save_with_barrier(index: int) -> None:
        barrier.wait()
        try:
            todos = [Todo(id=index, text=f"Task {index}", done=False)]
            storages[index].save(todos)
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(save_with_barrier, i) for i in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    assert len(errors) == 0, f"Concurrent saves raised errors: {errors}"


def test_sequential_saves_after_directory_created(tmp_path) -> None:
    """Issue #4790: Sequential saves should work correctly after directory is created."""
    db_path = tmp_path / "seq" / "todo.json"

    assert not db_path.parent.exists()

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="First task", done=False)]

    # First save creates the directory
    storage.save(todos)
    assert db_path.parent.exists()

    # Second save should work with existing directory
    todos.append(Todo(id=2, text="Second task", done=False))
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
