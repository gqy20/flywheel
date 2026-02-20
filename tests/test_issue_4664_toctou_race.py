"""Regression tests for issue #4664: TOCTOU race condition in _ensure_parent_directory.

Issue: exist_ok=False raises FileExistsError if concurrent process creates
directory between the exists() check and mkdir().

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import concurrent.futures
import json
import threading

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_mkdir_no_race_condition(tmp_path) -> None:
    """Issue #4664: Multiple threads creating parent directory should not raise FileExistsError.

    Before fix: FileExistsError is raised when concurrent threads try to create
    the same directory between exists() check and mkdir() call.
    After fix: Both threads should complete without error.
    """
    # Use a path where parent directory doesn't exist yet
    db_path = tmp_path / "new_dir" / "subdir" / "todo.json"

    errors: list[Exception] = []
    barrier = threading.Barrier(2)  # Synchronize both threads

    def create_directory():
        try:
            barrier.wait()  # Ensure both threads try at the same time
            _ensure_parent_directory(db_path)
        except Exception as e:
            errors.append(e)

    # Run two threads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_directory) for _ in range(2)]
        concurrent.futures.wait(futures)

    # After fix: No FileExistsError/OSError race condition should be raised
    race_errors = [e for e in errors if "File exists" in str(e) or isinstance(e, FileExistsError)]
    assert len(race_errors) == 0, f"Unexpected race condition errors: {race_errors}"


def test_concurrent_save_no_race_condition(tmp_path) -> None:
    """Issue #4664: Multiple processes calling save() concurrently should not raise FileExistsError.

    Before fix: FileExistsError is raised when concurrent processes try to save
    to the same new path.
    After fix: All saves should complete without FileExistsError.
    """
    db_path = tmp_path / "concurrent_dir" / "todos.json"
    storage = TodoStorage(str(db_path))

    errors: list[Exception] = []
    barrier = threading.Barrier(3)  # Synchronize all threads
    todo = Todo(id=1, text="test todo", done=False)

    def save_todos():
        try:
            barrier.wait()  # Ensure all threads try at the same time
            storage.save([todo])
        except FileExistsError as e:
            errors.append(e)
        except OSError:
            # OSError from temp file race is acceptable (atomic write)
            pass

    # Run multiple threads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(save_todos) for _ in range(3)]
        concurrent.futures.wait(futures)

    # After fix: No FileExistsError should be raised
    file_exists_errors = [e for e in errors if isinstance(e, FileExistsError)]
    assert len(file_exists_errors) == 0, f"Unexpected FileExistsError: {file_exists_errors}"

    # Verify final file content is valid JSON
    if db_path.exists():
        content = db_path.read_text()
        data = json.loads(content)
        assert isinstance(data, list)


def test_ensure_parent_directory_file_as_parent_still_fails(tmp_path) -> None:
    """Issue #4664: The fix should still reject file-as-directory cases with clear error.

    This is a regression test to ensure the fix doesn't break the security validation
    for file-as-directory confusion attacks.
    """
    # Create a file where we expect a directory
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("I am a file, not a directory")

    # Try to create a path that requires the file to be a directory
    db_path = conflicting_file / "subdir" / "todo.json"

    # Should still fail with clear error
    with pytest.raises(ValueError, match=r"(directory|path|not a directory|exists as a file)"):
        _ensure_parent_directory(db_path)
