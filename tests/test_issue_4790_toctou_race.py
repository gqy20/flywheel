"""Regression tests for issue #4790: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition between exists() check (line 43) and mkdir() call (line 45)
in _ensure_parent_directory. The exist_ok=False assumption is incorrect because
a concurrent process can create the directory between the check and mkdir.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import concurrent.futures
import threading

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_save_to_same_parent_directory_no_race(tmp_path) -> None:
    """Issue #4790: Two concurrent saves to same non-existent parent should not raise FileExistsError.

    Before fix: Concurrent processes can race on directory creation:
        1. Process A: checks parent.exists() -> False
        2. Process B: checks parent.exists() -> False
        3. Process B: calls mkdir() -> succeeds
        4. Process A: calls mkdir() -> FileExistsError!

    After fix: Using exist_ok=True handles the race condition gracefully.
    """
    # Create a path with non-existent parent directory
    shared_parent = tmp_path / "shared" / "deep" / "nested"
    db_path_a = shared_parent / "storage_a.json"
    db_path_b = shared_parent / "storage_b.json"

    errors = []
    barrier = threading.Barrier(2)  # Synchronize both threads

    def save_with_storage(db_path):
        try:
            barrier.wait()  # Ensure both threads start at the same time
            storage = TodoStorage(str(db_path))
            storage.save([Todo(id=1, text="test", done=False)])
        except Exception as e:
            errors.append(e)

    # Run two concurrent saves
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(save_with_storage, db_path_a)
        future_b = executor.submit(save_with_storage, db_path_b)

        future_a.result()
        future_b.result()

    # Should not raise FileExistsError due to race condition
    assert len(errors) == 0, f"Concurrent saves should not raise errors, got: {errors}"

    # Both files should be created successfully
    assert db_path_a.exists(), "Storage A file should exist"
    assert db_path_b.exists(), "Storage B file should exist"


def test_concurrent_ensure_parent_directory_no_file_exists_error(tmp_path) -> None:
    """Issue #4790: Direct test of _ensure_parent_directory race condition.

    This test directly exercises the race window in _ensure_parent_directory.
    """
    from flywheel.storage import _ensure_parent_directory

    # Create paths that share the same non-existent parent
    shared_parent = tmp_path / "race_test" / "dir"
    file_a = shared_parent / "file_a.json"
    file_b = shared_parent / "file_b.json"

    errors = []
    barrier = threading.Barrier(2)

    def ensure_parent(file_path):
        try:
            barrier.wait()  # Synchronize to maximize race window
            _ensure_parent_directory(file_path)
        except FileExistsError as e:
            # This is the specific error from the TOCTOU race
            errors.append(e)
        except Exception:
            pass  # Other errors are acceptable (e.g., already exists)

    # Run concurrent directory creation
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(ensure_parent, file_a)
        future_b = executor.submit(ensure_parent, file_b)

        future_a.result()
        future_b.result()

    # Should not raise FileExistsError
    assert len(errors) == 0, (
        f"_ensure_parent_directory should handle race condition, got FileExistsError: {errors}"
    )

    # Parent directory should exist
    assert shared_parent.exists(), "Parent directory should be created"


def test_sequential_saves_still_work_after_fix(tmp_path) -> None:
    """Issue #4790: Fix should not break normal sequential operation."""
    # Create storage with non-existent parent
    db_path = tmp_path / "new_dir" / "todos.json"
    storage = TodoStorage(str(db_path))

    # First save creates the directory
    storage.save([Todo(id=1, text="first", done=False)])
    assert db_path.exists()

    # Second save to existing directory should still work
    storage.save([Todo(id=1, text="second", done=True)])
    assert db_path.exists()

    # Verify content
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "second"
    assert todos[0].done is True
