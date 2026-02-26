"""Regression tests for issue #5983: TOCTOU race in _ensure_parent_directory.

Issue: There's a Time-of-Check-Time-of-Use (TOCTOU) race condition between
the validation loop that checks if parent paths are directories (not files)
and the subsequent mkdir call. An attacker could create a file between the
check and the mkdir, causing the operation to fail unexpectedly.

These tests verify that the race condition is handled gracefully with clear
error messages.
"""

from __future__ import annotations

import errno
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


class TestTOCTOURace:
    """Tests for TOCTOU race condition in _ensure_parent_directory."""

    def test_mkdir_race_with_file_created_at_parent_path(self, tmp_path) -> None:
        """Test that TOCTOU race where file is created at parent path is handled.

        Simulates a TOCTOU race where:
        1. _ensure_parent_directory checks that a parent path doesn't exist
        2. An attacker creates a file at that path between check and mkdir
        3. mkdir should fail with a clear ValueError about file-as-directory

        This test specifically targets the TOCTOU vulnerability described in issue #5983.
        """
        # Target path: tmp_path / "parent" / "child" / "db.json"
        # We'll create a file at "parent" during the race window
        parent_dir = tmp_path / "parent"
        target_path = parent_dir / "child" / "db.json"

        original_mkdir = Path.mkdir

        def race_mkdir(self, *args, **kwargs):
            # Before mkdir, create a file at the parent path (simulating TOCTOU race)
            if self == parent_dir:
                # Create a file where directory should be created
                parent_dir.write_text("attacker file created during race")
            return original_mkdir(self, *args, **kwargs)

        # Call _ensure_parent_directory with patched mkdir that simulates the race
        with patch.object(Path, "mkdir", race_mkdir), pytest.raises(
            (OSError, ValueError)
        ) as exc_info:
            _ensure_parent_directory(target_path)

        # The error should clearly indicate file-as-directory problem
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["file", "directory", "not a directory", "exists"]
        ), f"Error message should mention file/directory issue, got: {exc_info.value}"

    def test_concurrent_mkdir_with_exist_ok_handles_graceful_race(self, tmp_path) -> None:
        """Test that concurrent mkdir calls succeed with exist_ok=True.

        When multiple threads call _ensure_parent_directory for paths sharing
        the same parent directory, all should succeed. The race where one
        thread creates the directory before another's mkdir call should be
        handled gracefully (not raise FileExistsError).
        """
        results = []
        errors = []
        num_threads = 10

        def worker(worker_id: int):
            try:
                # All workers target files in the same new directory
                target = tmp_path / "shared_parent" / f"file_{worker_id}.json"
                _ensure_parent_directory(target)
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should succeed (race handled gracefully)
        assert len(results) == num_threads, (
            f"Expected all {num_threads} threads to succeed, but got {len(results)}. "
            f"Errors: {errors}"
        )

    def test_save_handles_file_created_at_parent_during_race(self, tmp_path) -> None:
        """Test that TodoStorage.save handles file-as-directory race with clear error."""
        db_path = tmp_path / "newdir" / "subdir" / "todo.json"
        storage = TodoStorage(str(db_path))
        parent_dir = tmp_path / "newdir"

        original_mkdir = Path.mkdir

        def race_mkdir(self, *args, **kwargs):
            # Simulate TOCTOU: create a file at parent during race window
            if self == parent_dir:
                parent_dir.write_text("race file")
                # Now mkdir will fail because file exists
                raise FileExistsError(errno.EEXIST, f"File exists: '{self}'")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", race_mkdir), pytest.raises(
            (OSError, ValueError)
        ) as exc_info:
            storage.save([Todo(id=1, text="test")])

        # Error should be descriptive about the file-as-directory issue
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["file", "directory", "exists", "failed", "path"]
        ), f"Error message should be descriptive, got: {exc_info.value}"


class TestFileExistsErrorHandling:
    """Tests for proper FileExistsError handling in _ensure_parent_directory."""

    def test_file_exists_at_parent_raises_clear_error(self, tmp_path) -> None:
        """Test that FileExistsError at parent path produces clear error message."""
        parent_path = tmp_path / "blocked"
        target_path = parent_path / "file.json"

        # Pre-create a file at the parent path
        parent_path.write_text("blocking file")

        # Should raise with clear message
        with pytest.raises(ValueError) as exc_info:
            _ensure_parent_directory(target_path)

        error_msg = str(exc_info.value).lower()
        assert "file" in error_msg or "directory" in error_msg
        assert "blocked" in error_msg

    def test_directory_created_concurrently_succeeds(self, tmp_path) -> None:
        """Test that if directory is created concurrently, operation succeeds.

        This is the expected behavior when exist_ok=True is used:
        if another process creates the directory between our check and mkdir,
        we should succeed (not fail with FileExistsError).
        """
        target_path = tmp_path / "concurrent" / "file.json"
        parent = target_path.parent

        # Verify parent doesn't exist initially
        assert not parent.exists()

        # Simulate: another process creates the directory concurrently
        parent.mkdir(parents=True)

        # Now call _ensure_parent_directory - should succeed without error
        # because the directory now exists (race is handled gracefully)
        _ensure_parent_directory(target_path)

        # Verify the directory exists and is a directory
        assert parent.is_dir()

    def test_file_created_concurrently_fails_with_clear_error(self, tmp_path) -> None:
        """Test that if file is created concurrently, fails with clear error.

        This tests the TOCTOU race specifically:
        1. Our validation loop passes (path doesn't exist)
        2. Attacker creates a file at the path
        3. Our mkdir fails, and we should detect it's a file (not directory)

        Issue #5983: The fix should detect when FileExistsError is due to a file
        (not directory) and provide a clear error message.
        """
        parent_path = tmp_path / "race_target"
        target_path = parent_path / "data.json"

        original_mkdir = Path.mkdir

        def race_mkdir(self, *args, **kwargs):
            # Simulate the TOCTOU race: file created between check and mkdir
            if self == parent_path:
                # Create file at parent path
                parent_path.write_text("created during race")
                # Now mkdir will fail because file exists
                try:
                    return original_mkdir(self, *args, **kwargs)
                except FileExistsError:
                    raise
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", race_mkdir), pytest.raises(ValueError) as exc_info:
            _ensure_parent_directory(target_path)

        # Verify the error message clearly indicates file-as-directory issue
        error_msg = str(exc_info.value).lower()
        # The fix should produce an error mentioning "file" and "directory"
        # (not just generic "failed to create directory" or "file exists")
        assert "file" in error_msg, (
            f"Error message should mention 'file', got: {exc_info.value}"
        )
        assert "directory" in error_msg, (
            f"Error message should mention 'directory', got: {exc_info.value}"
        )

    def test_file_created_concurrently_shows_path_in_error(self, tmp_path) -> None:
        """Test that TOCTOU race error includes the problematic path in message."""
        parent_path = tmp_path / "problem_path"
        target_path = parent_path / "data.json"

        original_mkdir = Path.mkdir

        def race_mkdir(self, *args, **kwargs):
            if self == parent_path:
                # Create file at parent path to trigger race
                parent_path.write_text("attacker content")
                try:
                    return original_mkdir(self, *args, **kwargs)
                except FileExistsError:
                    raise
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", race_mkdir), pytest.raises(ValueError) as exc_info:
            _ensure_parent_directory(target_path)

        # Error message should include the specific path that caused the issue
        error_msg = str(exc_info.value)
        assert "problem_path" in error_msg, (
            f"Error message should include the problematic path, got: {exc_info.value}"
        )
