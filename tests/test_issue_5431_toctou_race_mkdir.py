"""Regression tests for issue #5431: TOCTOU race in _ensure_parent_directory.

Issue: Between checking parent.exists() and calling parent.mkdir(exist_ok=False),
another process could create the directory. This causes FileExistsError due to
the race condition.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import concurrent.futures
import threading

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


class TestTOCTOURaceConcurrentMkdir:
    """Tests for TOCTOU race condition between validation and mkdir."""

    def test_concurrent_ensure_parent_directory_no_race(self, tmp_path) -> None:
        """Issue #5431: Concurrent calls should not raise FileExistsError.

        Before fix: If two processes check parent.exists() simultaneously (both see False)
        and then both try mkdir(exist_ok=False), the second will raise FileExistsError.
        After fix: Using exist_ok=True allows both to succeed gracefully.
        """
        # Create a path where parent doesn't exist
        db_path = tmp_path / "newdir" / "subdir" / "test.json"
        parent_path = db_path.parent

        # Ensure parent doesn't exist before test
        assert not parent_path.exists()

        # Barrier to synchronize both threads
        barrier = threading.Barrier(2)
        errors = []
        results = []

        def ensure_parent():
            try:
                # Wait for both threads to be ready
                barrier.wait()
                _ensure_parent_directory(db_path)
                results.append("success")
            except Exception as e:
                errors.append(e)

        # Run two threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(ensure_parent) for _ in range(2)]
            concurrent.futures.wait(futures)

        # Both should succeed - no FileExistsError from race
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 2
        # Parent should exist after
        assert parent_path.exists()

    def test_concurrent_save_operations_no_race(self, tmp_path) -> None:
        """Issue #5431: Concurrent save() calls should not raise FileExistsError.

        This is the real-world scenario: two TodoStorage.save() calls trying to
        create the same parent directory simultaneously.
        """
        # Create storage paths with same parent that doesn't exist
        db_path = tmp_path / "shared_parent" / "data.json"
        storage = TodoStorage(str(db_path))

        # Ensure parent doesn't exist before test
        assert not db_path.parent.exists()

        # Barrier to synchronize both threads
        barrier = threading.Barrier(2)
        errors = []
        results = []

        def save_todos():
            try:
                barrier.wait()
                storage.save([])
                results.append("success")
            except Exception as e:
                errors.append(e)

        # Run two threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(save_todos) for _ in range(2)]
            concurrent.futures.wait(futures)

        # Both should succeed - no FileExistsError from race
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 2

    def test_file_as_directory_still_detected(self, tmp_path) -> None:
        """Issue #5431: Fix must still detect file-as-directory confusion.

        The fix for TOCTOU must not break the security check that prevents
        treating a file as a directory.
        """
        # Create a file where a directory should be
        blocking_file = tmp_path / "blocking_file"
        blocking_file.write_text("I am a file")

        # Try to create a path that would require the file to be a directory
        db_path = blocking_file / "subdir" / "test.json"

        # Should still raise ValueError for file-as-directory
        with pytest.raises(ValueError, match=r"(file|directory|not a directory)"):
            _ensure_parent_directory(db_path)

    def test_directory_created_successfully_after_fix(self, tmp_path) -> None:
        """Issue #5431: Normal directory creation should still work."""
        db_path = tmp_path / "new" / "nested" / "dir" / "test.json"

        # Should succeed
        _ensure_parent_directory(db_path)

        # Parent should exist
        assert db_path.parent.exists()
        assert db_path.parent.is_dir()
