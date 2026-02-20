"""Regression tests for issue #4664: TOCTOU race condition in _ensure_parent_directory.

Issue: exist_ok=False in mkdir() raises FileExistsError when concurrent process
creates the directory between the exists() check and mkdir() call.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_mkdir_no_race_condition(tmp_path: Path) -> None:
    """Issue #4664: Multiple threads calling save() concurrently should not raise FileExistsError.

    Simulates the TOCTOU race condition where one thread checks parent.exists()
    while another thread creates the directory, causing mkdir(exist_ok=False) to fail.
    """
    # Use a shared path that doesn't exist yet (triggers mkdir)
    shared_db_path = tmp_path / "concurrent" / "db.json"

    errors: list[Exception] = []
    success_count: list[int] = [0]
    barrier = threading.Barrier(2)  # Synchronize both threads to maximize race window

    def save_todos() -> None:
        storage = TodoStorage(str(shared_db_path))
        barrier.wait()  # Synchronize start
        try:
            storage.save([Todo(id=1, text="test", done=False)])
            success_count[0] += 1
        except Exception as e:
            errors.append(e)

    # Run two threads concurrently
    thread1 = threading.Thread(target=save_todos)
    thread2 = threading.Thread(target=save_todos)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    # Check for TOCTOU race condition errors
    # The code catches FileExistsError and re-raises as OSError with "File exists" message
    race_condition_errors = [e for e in errors if "file exists" in str(e).lower()]
    assert len(race_condition_errors) == 0, (
        f"TOCTOU race condition detected! Errors: {race_condition_errors}"
    )

    # At least one thread should have succeeded
    assert success_count[0] >= 1, (
        f"At least one thread should succeed. Errors: {[str(e) for e in errors]}"
    )


def test_concurrent_mkdir_multiple_threads(tmp_path: Path) -> None:
    """Issue #4664: Stress test with multiple threads to expose race condition."""
    shared_db_path = tmp_path / "stress" / "db.json"
    num_threads = 10
    errors: list[Exception] = []
    barrier = threading.Barrier(num_threads)

    def save_todos() -> None:
        storage = TodoStorage(str(shared_db_path))
        barrier.wait()
        try:
            storage.save([])
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=save_todos) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No thread should have raised OSError wrapping FileExistsError
    file_exists_errors = [e for e in errors if "file exists" in str(e).lower()]
    assert len(file_exists_errors) == 0, (
        f"Found {len(file_exists_errors)} OSError/FileExistsError(s) indicating race condition: {file_exists_errors}"
    )


def test_file_as_directory_validation_still_works(tmp_path: Path) -> None:
    """Issue #4664: File-as-directory validation should still catch path confusion.

    After changing to exist_ok=True, we must ensure that file-as-directory
    validation (lines 35-40 in storage.py) still catches the security issue.
    """
    # Create a file where we expect a directory
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("I am a file")

    # Try to create db at path that requires the file to be a directory
    db_path = conflicting_file / "data.json"
    storage = TodoStorage(str(db_path))

    # Should raise ValueError, not FileExistsError
    with pytest.raises(ValueError, match=r"(directory|not a directory)"):
        storage.save([])
