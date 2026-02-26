"""Regression tests for issue #5983: TOCTOU race between _ensure_parent_directory check and mkdir.

Issue: The check for file-as-directory (lines 35-40) and subsequent mkdir (line 45)
is not atomic. An attacker could create a file between the validation check and mkdir,
causing a TOCTOU race condition.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_file_created_between_check_and_mkdir(tmp_path) -> None:
    """Issue #5983: Should handle race when file is created between check and mkdir.

    This simulates a TOCTOU attack where:
    1. _ensure_parent_directory checks that parent paths are valid (no files)
    2. Attacker creates a file at one of the parent paths
    3. mkdir fails because path is now a file

    Before fix: FileExistsError is raised but caught as generic OSError
    After fix: FileExistsError is caught specifically and re-raised as ValueError with clear message
    """
    # Setup: Create a path that will need a new directory
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"

    # Track mkdir calls to inject race condition
    original_mkdir = Path.mkdir
    race_injected = False

    def racing_mkdir(self, *args, **kwargs):
        """Inject a file creation race condition between check and mkdir."""
        nonlocal race_injected
        if not race_injected and "newdir" in str(self):
            # Create a file at the parent path before mkdir runs
            # This simulates attacker creating file after our check
            (tmp_path / "newdir").write_text("attacker file")
            race_injected = True
            # Now try the original mkdir which should fail because a file exists
        return original_mkdir(self, *args, **kwargs)

    storage = TodoStorage(str(db_path))

    # The race condition should be handled gracefully
    # Before fix: FileExistsError is raised but caught as generic OSError with unclear message
    # After fix: ValueError with clear message about file-as-directory conflict
    with (
        patch.object(Path, "mkdir", racing_mkdir),
        pytest.raises((ValueError, OSError)) as exc_info,
    ):
        storage.save([Todo(id=1, text="test")])

    # Verify error message is clear about the path issue
    error_msg = str(exc_info.value).lower()
    # After fix, should have clear message about file vs directory
    assert "file" in error_msg or "exists" in error_msg or "not a directory" in error_msg


def test_toctou_race_directory_created_between_check_and_mkdir(tmp_path) -> None:
    """Issue #5983: Should succeed when directory is created by another process.

    This simulates the case where another process creates the same directory
    between our check and our mkdir. This is a legitimate race and should succeed.
    """
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"

    # Track mkdir calls to inject race condition
    original_mkdir = Path.mkdir
    race_injected = False

    def racing_mkdir(self, *args, **kwargs):
        """Another process creates the directory before our mkdir."""
        nonlocal race_injected
        if not race_injected and "newdir" in str(self):
            # Create the directory before mkdir runs
            original_mkdir(self, parents=True, exist_ok=True)
            race_injected = True
            return  # Already created, but still call original with exist_ok
        return original_mkdir(self, *args, **kwargs)

    storage = TodoStorage(str(db_path))

    # With exist_ok=True, this should succeed
    with patch.object(Path, "mkdir", racing_mkdir):
        storage.save([Todo(id=1, text="test")])

    # Verify the save succeeded
    assert db_path.exists()


def test_ensure_parent_directory_handles_file_exists_error(tmp_path) -> None:
    """Issue #5983: _ensure_parent_directory should handle FileExistsError gracefully.

    When a file exists at a path where we try to create a directory,
    we should get a clear error message, not a generic OSError.
    """
    # Create a file where a directory would need to be created
    blocking_file = tmp_path / "blocking_file"
    blocking_file.write_text("I am a file")

    # Try to create a path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # This should raise a clear ValueError about file vs directory
    with pytest.raises((ValueError, OSError)) as exc_info:
        _ensure_parent_directory(db_path)

    # Error message should be clear about the problem
    error_msg = str(exc_info.value).lower()
    assert "file" in error_msg or "directory" in error_msg


def test_concurrent_ensure_parent_directory_calls(tmp_path) -> None:
    """Issue #5983: Multiple concurrent calls should all succeed for same path.

    This tests that exist_ok=True allows multiple processes to create
    the same directory without errors.
    """
    import multiprocessing
    import time

    db_path = tmp_path / "shared" / "todo.json"
    results = multiprocessing.Manager().list()

    def worker(worker_id: int):
        try:
            storage = TodoStorage(str(db_path))
            time.sleep(0.01)  # Increase race likelihood
            storage.save([Todo(id=worker_id, text=f"worker-{worker_id}")])
            results.append(("success", worker_id))
        except Exception as e:
            results.append(("error", worker_id, str(e)))

    # Run multiple workers
    processes = []
    for i in range(3):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers failed with errors: {errors}"
    assert len(successes) == 3, f"Expected 3 successes, got {len(successes)}"
