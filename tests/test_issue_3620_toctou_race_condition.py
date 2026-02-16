"""Regression tests for issue #3620: TOCTOU race condition in _ensure_parent_directory.

Issue: Time-of-check-time-of-use race condition exists between:
1. Line 43: `if not parent.exists()` - checking if parent directory exists
2. Line 45: `parent.mkdir(parents=True, exist_ok=False)` - creating directory

If another process creates the directory between these two operations, the
mkdir with exist_ok=False will raise OSError (FileExistsError), even though
the directory creation is the desired outcome.

Fix: Use exist_ok=True in mkdir() to handle the race condition gracefully.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_directory_created_between_check_and_mkdir(tmp_path) -> None:
    """Issue #3620: Test that race condition in directory creation is handled.

    This test directly simulates the race condition where another process
    creates the parent directory between our check and our mkdir call.

    Before fix: mkdir with exist_ok=False raises FileExistsError
    After fix: mkdir with exist_ok=True succeeds silently
    """
    db_path = tmp_path / "nested" / "dir" / "db.json"
    parent_dir = db_path.parent

    # Save the original mkdir method
    original_mkdir = Path.mkdir

    def mock_mkdir_race(self, mode=0o777, parents=False, exist_ok=False):
        """Mock mkdir that simulates TOCTOU race - directory created by another process."""
        if self == parent_dir:
            # Simulate another process creating the directory before our mkdir
            if not self.exists():
                original_mkdir(self, mode=mode, parents=parents, exist_ok=True)

            # Now if exist_ok=False, this will raise FileExistsError
            # This is the bug - even though directory creation succeeded elsewhere
            if not exist_ok and self.exists():
                raise FileExistsError(f"[Errno 17] File exists: '{self}'")
            return
        return original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    # Patch mkdir on this specific Path instance
    with patch.object(Path, "mkdir", mock_mkdir_race):
        # Before fix: This raises FileExistsError
        # After fix: This succeeds because exist_ok=True
        _ensure_parent_directory(db_path)

    # Verify directory exists
    assert parent_dir.exists()


def test_toctou_race_with_concurrent_process(tmp_path) -> None:
    """Issue #3620: Test concurrent directory creation from multiple processes.

    Multiple processes trying to create the same nested parent directory
    should not fail with OSError. All should succeed.
    """
    db_base = tmp_path / "shared" / "nested" / "db.json"
    results = multiprocessing.Queue()

    def worker(worker_id: int):
        """Worker that tries to save to the same path."""
        try:
            storage = TodoStorage(str(db_base))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            results.put(("success", worker_id))
        except OSError as e:
            # OSError with "File exists" indicates TOCTOU race condition
            results.put(("error", worker_id, str(e)))
        except Exception as e:
            results.put(("error", worker_id, str(e)))

    # Start multiple processes concurrently
    num_workers = 5
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    worker_results = []
    while not results.empty():
        worker_results.append(results.get())

    successes = [r for r in worker_results if r[0] == "success"]
    errors = [r for r in worker_results if r[0] == "error"]

    # All workers should succeed without OSError
    assert len(errors) == 0, f"Workers encountered errors (possible TOCTOU race): {errors}"
    assert len(successes) == num_workers


def test_file_as_directory_check_still_works_after_fix(tmp_path) -> None:
    """Issue #3620: Verify file-as-directory validation still works after TOCTOU fix.

    The fix for TOCTOU should not compromise the file-as-directory validation
    that protects against path confusion attacks.
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create a db that requires this file to be a directory
    db_path = blocking_file / "subdir" / "db.json"

    # Should raise ValueError for file-as-directory confusion
    with pytest.raises(ValueError, match=r"(file|directory|not a directory)"):
        _ensure_parent_directory(db_path)


def test_normal_nested_directory_creation_works(tmp_path) -> None:
    """Issue #3620: Normal nested directory creation should still work."""
    db_path = tmp_path / "a" / "b" / "c" / "db.json"

    # Should succeed without error
    _ensure_parent_directory(db_path)

    # Verify parent directory was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_existing_parent_directory_is_handled(tmp_path) -> None:
    """Issue #3620: When parent already exists, no error should be raised."""
    db_path = tmp_path / "existing" / "db.json"

    # Pre-create parent directory
    db_path.parent.mkdir(parents=True)

    # Should succeed without error
    _ensure_parent_directory(db_path)

    # Verify parent still exists
    assert db_path.parent.exists()
