"""Regression tests for issue #2179: Race condition in _ensure_parent_directory.

Issue: FileExistsError during concurrent directory creation due to exist_ok=False.
The exists() check at line 43 and mkdir() at line 45 have a race condition window.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


def _create_parent_directory_task(path_str: str, results: list) -> None:
    """Helper function for concurrent testing - creates parent directory."""
    try:
        _ensure_parent_directory(Path(path_str))
        results.append(("success", None))
    except FileExistsError as e:
        results.append(("FileExistsError", str(e)))
    except Exception as e:
        results.append(("error", type(e).__name__, str(e)))


def test_concurrent_directory_creation_no_race():
    """Issue #2179: Two concurrent processes creating the same parent directory should both succeed.

    This test simulates the race condition where:
    1. Process A checks parent.exists() -> False
    2. Process B checks parent.exists() -> False
    3. Process A calls mkdir() -> succeeds
    4. Process B calls mkdir() with exist_ok=False -> FileExistsError (BUG!)

    After fix: Both processes should succeed because exist_ok=True handles the race.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use the same non-existent parent path for both "concurrent" calls
        parent_dir = Path(tmpdir) / "race_test" / "nested"
        file_path = parent_dir / "todo.json"

        # Use multiprocessing.Manager for shared list
        manager = multiprocessing.Manager()
        results = manager.list()

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(processes=2) as pool:
            args = [(str(file_path), results) for _ in range(2)]
            pool.starmap(_create_parent_directory_task, args)
            pool.close()
            pool.join()

        # Both calls should succeed - no FileExistsError
        results_list = list(results)
        file_exists_errors = [r for r in results_list if r[0] == "FileExistsError"]
        assert len(file_exists_errors) == 0, f"Got FileExistsError in concurrent calls: {file_exists_errors}"

        # At least one should have succeeded
        successes = [r for r in results_list if r[0] == "success"]
        assert len(successes) >= 1, "At least one process should succeed"

        # Directory should exist now
        assert parent_dir.exists(), "Parent directory should be created"
        assert parent_dir.is_dir(), "Parent should be a directory"


def test_ensure_parent_directory_idempotent():
    """Issue #2179: Calling _ensure_parent_directory multiple times on same path should succeed.

    This is a simpler version of the race condition test that doesn't use multiprocessing.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        parent_dir = Path(tmpdir) / "idempotent_test" / "nested"
        file_path = parent_dir / "todo.json"

        # First call - directory doesn't exist, should create it
        _ensure_parent_directory(file_path)
        assert parent_dir.exists()
        assert parent_dir.is_dir()

        # Second call - directory exists, should succeed with exist_ok=True
        # This demonstrates that the race condition is fixed
        _ensure_parent_directory(file_path)

        # Third call - should still work
        _ensure_parent_directory(file_path)

        # Verify the directory still exists and is a directory
        assert parent_dir.exists()
        assert parent_dir.is_dir()


def test_file_as_directory_validation_still_works():
    """Issue #2179: The fix should not break file-as-directory validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file where a directory should be
        conflicting_file = Path(tmpdir) / "blocking_file.json"
        conflicting_file.write_text("I am a file")

        # Try to create a path that requires the file to be a directory
        file_path = conflicting_file / "nested" / "todo.json"

        # Should still raise ValueError for file-as-directory confusion
        with pytest.raises(ValueError, match=r"exists as a file"):
            _ensure_parent_directory(file_path)
