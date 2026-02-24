"""Regression tests for issue #5596: TOCTOU race in parent validation and mkdir.

Issue: _ensure_parent_directory() validates parent paths first, then creates
directories with exist_ok=False. This leaves a race window where an attacker
could create a symlink between validation and mkdir, potentially bypassing
security checks.

The fix should use exist_ok=True with proper error handling, making the
directory creation atomic from the perspective of race conditions.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_mkdir_race_with_concurrent_directory_creation(tmp_path) -> None:
    """Issue #5596: mkdir with exist_ok=False fails if directory is created concurrently.

    The current code validates parent paths, then uses exist_ok=False for mkdir.
    If another process/thread creates the directory between validation and mkdir,
    the operation will fail with FileExistsError.

    After fix: mkdir with exist_ok=True should handle this gracefully.
    """
    db_path = tmp_path / "subdir" / "todo.json"

    # Create the parent directory concurrently right before mkdir is called
    mkdir_call_count = [0]
    original_mkdir = Path.mkdir

    def patched_mkdir(self, *args, **kwargs):
        mkdir_call_count[0] += 1
        # On the first mkdir call, create the directory before the original call
        if mkdir_call_count[0] == 1:
            # Simulate race: another process creates the directory
            original_mkdir(self, parents=True, exist_ok=True)
        # Now call the original (which might fail if exist_ok=False)
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", patched_mkdir):
        storage = TodoStorage(str(db_path))
        # This should NOT raise FileExistsError
        storage.save([Todo(id=1, text="test")])

    # Verify save succeeded
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_ensure_parent_directory_is_idempotent_with_exist_ok_true(tmp_path) -> None:
    """Issue #5596: _ensure_parent_directory should be safe to call multiple times.

    After fix: Using exist_ok=True makes the operation idempotent and race-safe.
    """
    db_path = tmp_path / "subdir" / "todo.json"

    # Call _ensure_parent_directory twice
    _ensure_parent_directory(db_path)
    _ensure_parent_directory(db_path)

    # Should not raise any errors
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_concurrent_save_creates_parent_safely(tmp_path) -> None:
    """Issue #5596: Multiple threads creating parent directory should not race.

    Before fix: One thread might fail with FileExistsError
    After fix: All threads should succeed (idempotent directory creation)
    """
    errors = []
    success_count = [0]
    lock = threading.Lock()

    def worker(worker_id: int) -> None:
        try:
            # Each worker uses a different db in a shared parent directory
            db_path = tmp_path / "shared_parent" / f"db_{worker_id}.json"
            storage = TodoStorage(str(db_path))
            storage.save([Todo(id=1, text=f"worker-{worker_id}")])
            with lock:
                success_count[0] += 1
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Start multiple threads that will all try to create the same parent
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # Start all threads roughly simultaneously
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5)

    # All threads should succeed
    assert len(errors) == 0, f"Threads encountered errors: {errors}"
    assert success_count[0] == 10, f"Expected 10 successes, got {success_count[0]}"


def test_parent_validation_still_detects_file_as_parent(tmp_path) -> None:
    """Issue #5596: After fix, should still detect when parent path is a file.

    The race condition fix should not compromise the validation that detects
    when a path component is a file (not a directory).
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create db inside this file (impossible)
    db_path = blocking_file / "subdir" / "todo.json"

    with pytest.raises(ValueError, match=r"(file|not a directory)"):
        _ensure_parent_directory(db_path)


def test_mkdir_uses_exist_ok_true_after_fix(tmp_path) -> None:
    """Issue #5596: Verify the fix uses exist_ok=True for mkdir.

    This test verifies the implementation detail of the fix.
    """
    db_path = tmp_path / "newdir" / "todo.json"

    exist_ok_values = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        exist_ok_values.append(kwargs.get("exist_ok", args[1] if len(args) > 1 else False))
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", tracking_mkdir):
        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test")])

    # The fix should use exist_ok=True
    assert len(exist_ok_values) > 0, "mkdir should have been called"
    assert any(exist_ok is True for exist_ok in exist_ok_values), (
        f"mkdir should be called with exist_ok=True, got: {exist_ok_values}"
    )
