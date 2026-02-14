"""Regression tests for issue #3226: TOCTOU race condition in _ensure_parent_directory.

Issue: TOCTOU race condition between path existence check and mkdir in
_ensure_parent_directory function at line 43-45 of src/flywheel/storage.py.

The race window occurs between:
    if not parent.exists():  # Check
        parent.mkdir(parents=True, exist_ok=False)  # Use

If another process creates the directory between these two operations,
mkdir() with exist_ok=False raises FileExistsError even though we already
verified the directory doesn't exist.

This test should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import concurrent.futures

import pytest

from flywheel.storage import TodoStorage


def test_concurrent_save_no_toctou_race(tmp_path) -> None:
    """Issue #3226: Concurrent save() calls should not fail with FileExistsError from mkdir race.

    Before fix: Multiple concurrent save() calls could race between exists() check
    and mkdir() call, causing FileExistsError when both processes try to mkdir.

    After fix: Using exist_ok=True or catching FileExistsError ensures that concurrent
    directory creation succeeds without race-condition errors.
    """
    # Create a path where the parent doesn't exist yet
    db_path = tmp_path / "nested" / "deep" / "db.json"

    # Number of concurrent processes
    num_workers = 10

    errors = []

    def concurrent_save(worker_id: int) -> str:
        """Attempt to save concurrently - should not fail due to mkdir race."""
        try:
            # Each worker creates its own storage instance to simulate independent processes
            worker_storage = TodoStorage(str(db_path))
            worker_storage.save([])
            return f"worker_{worker_id}_success"
        except Exception as e:
            errors.append((worker_id, type(e).__name__, str(e)))
            raise

    # Run concurrent saves - all should succeed without FileExistsError
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(concurrent_save, i) for i in range(num_workers)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All workers should succeed
    assert len(results) == num_workers, f"All {num_workers} concurrent saves should succeed"


def test_toctou_file_as_directory_still_errors(tmp_path) -> None:
    """Issue #3226: After race fix, file-as-directory errors should still be properly detected.

    This test ensures that the race fix doesn't inadvertently allow file-as-directory
    confusion attacks to succeed.
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking_file.json"
    blocking_file.write_text("I am a file, not a directory")

    # Try to create database inside this file
    db_path = blocking_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with ValueError indicating the path issue
    with pytest.raises(ValueError, match=r"(file|directory|exists)"):
        storage.save([])


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #3226: Normal nested directory creation should continue to work after fix."""
    # Create a deeply nested path
    db_path = tmp_path / "level1" / "level2" / "level3" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed without any errors
    storage.save([])

    # Verify directory was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_parent_already_exists_concurrent_saves(tmp_path) -> None:
    """Issue #3226: Concurrent saves when parent exists should also work."""
    # Pre-create the parent directory
    parent_dir = tmp_path / "existing_parent"
    parent_dir.mkdir()
    db_path = parent_dir / "todo.json"

    num_workers = 5
    errors = []

    def concurrent_save(worker_id: int) -> str:
        try:
            worker_storage = TodoStorage(str(db_path))
            worker_storage.save([])
            return f"worker_{worker_id}_success"
        except Exception as e:
            errors.append((worker_id, type(e).__name__, str(e)))
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(concurrent_save, i) for i in range(num_workers)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_workers
