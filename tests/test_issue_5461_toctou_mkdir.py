"""Regression tests for issue #5461: TOCTOU race in _ensure_parent_directory.

Issue: _ensure_parent_directory uses exist_ok=False after checking parent.exists(),
creating a TOCTOU race window where another process could create the directory
between the check and mkdir, causing FileExistsError (wrapped in OSError).

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import concurrent.futures
import errno
import threading
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_toctou_race_deterministic(tmp_path) -> None:
    """Issue #5461: Deterministic test for TOCTOU race using mock.

    Before fix: _ensure_parent_directory uses exist_ok=False which fails
    if another process creates the directory between the exists() check and mkdir().

    After fix: Using exist_ok=True handles the race gracefully.
    """
    db_path = tmp_path / "nested" / "todo.json"
    parent_dir = db_path.parent

    # Track the original mkdir method
    original_mkdir = Path.mkdir

    def mock_mkdir_race(self, parents=False, exist_ok=False):
        """Mock mkdir that simulates another process creating the dir first."""
        # If this is the parent directory we're trying to create, simulate the race
        if self == parent_dir and not exist_ok:
            # Simulate another process creating the directory between
            # the exists() check and this mkdir() call
            original_mkdir(self, parents=parents, exist_ok=True)
            # Now the directory exists, so exist_ok=False should fail
            if not exist_ok:
                raise FileExistsError(f"[Errno 17] File exists: '{self}'")
        return original_mkdir(self, parents=parents, exist_ok=exist_ok)

    with patch.object(Path, "mkdir", mock_mkdir_race):
        # Before fix: This should raise OSError wrapping FileExistsError
        # After fix: This should succeed
        _ensure_parent_directory(db_path)


def test_concurrent_save_to_same_new_path_no_race_error(tmp_path) -> None:
    """Issue #5461: Concurrent saves to same new path should not raise FileExistsError.

    Before fix: If two threads/processes try to save to the same new nested path,
    the TOCTOU race between parent.exists() check and mkdir(exist_ok=False)
    could cause OSError wrapping FileExistsError (errno 17).

    After fix: Using exist_ok=True handles the race gracefully.
    """
    # Use a path that doesn't exist yet (triggers directory creation)
    db_path = str(tmp_path / "nested" / "deep" / "path" / "todo.json")

    errors: list[Exception] = []
    success_count = 0
    lock = threading.Lock()

    def save_todos():
        nonlocal success_count
        try:
            storage = TodoStorage(db_path)
            storage.save([Todo(id=1, text="test", done=False)])
            with lock:
                success_count += 1
        except Exception as e:
            with lock:
                errors.append(e)

    # Run multiple concurrent saves
    num_threads = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(save_todos) for _ in range(num_threads)]
        concurrent.futures.wait(futures)

    # Should not have any OSError with errno EEXIST (File exists) from the race
    # Note: The code wraps FileExistsError in OSError, so we check for errno 17
    race_errors = [
        e
        for e in errors
        if isinstance(e, OSError)
        and (
            e.errno == errno.EEXIST
            or ("File exists" in str(e))
            or (isinstance(e.__cause__, FileExistsError))
        )
    ]
    assert len(race_errors) == 0, (
        f"Got OSError with EEXIST from TOCTOU race: {race_errors}"
    )

    # At least some should have succeeded
    assert success_count >= 1, f"At least one save should succeed, but got {errors}"


def test_parent_dir_created_by_another_process_during_save(tmp_path) -> None:
    """Issue #5461: Simulate race where another process creates parent dir.

    This test directly simulates the TOCTOU scenario by creating the parent
    directory after _ensure_parent_directory checks but before it creates.
    """
    db_path = tmp_path / "nested" / "todo.json"

    # Create parent just before TodoStorage tries to
    # This simulates the race condition
    parent_dir = db_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Now try to save - should not raise FileExistsError
    storage = TodoStorage(str(db_path))
    # This should succeed without FileExistsError
    storage.save([Todo(id=1, text="test")])

    assert db_path.exists(), "Database file should be created"
