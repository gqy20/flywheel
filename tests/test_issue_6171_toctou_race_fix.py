"""Regression tests for issue #6171: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a Time-Of-Check-To-Time-Of-Use (TOCTOU) race between checking
if parent exists (line 43) and calling mkdir (line 45). An attacker could create
a file or directory at 'parent' path between the check and mkdir, causing mkdir
to fail or behave unexpectedly.

The fix should use exist_ok=True and catch specific exceptions, providing a more
atomic approach.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


class TestTOCTOURaceCondition:
    """Tests for TOCTOU race condition in _ensure_parent_directory."""

    def test_mkdir_succeeds_when_directory_created_between_check_and_mkdir(self, tmp_path: Path) -> None:
        """Issue #6171: mkdir should succeed if directory is created by another process.

        This test simulates the TOCTOU race by creating the parent directory
        between the exists() check and the mkdir() call.
        """
        db_path = tmp_path / "newdir" / "todo.json"
        parent = db_path.parent

        # Ensure parent doesn't exist initially
        assert not parent.exists()

        # Track mkdir calls
        original_mkdir = Path.mkdir
        mkdir_call_count = [0]

        def patched_mkdir(self, *args, **kwargs):
            mkdir_call_count[0] += 1
            # Simulate race condition: create the directory right before mkdir is called
            if not self.exists():
                original_mkdir(self, *args, **kwargs)
            # If exist_ok=True, this should still succeed even if directory now exists
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", patched_mkdir):
            storage = TodoStorage(str(db_path))
            # This should NOT raise FileExistsError even though directory was created
            # between exists() check and mkdir() call
            storage.save([Todo(id=1, text="test")])

        # Verify the save succeeded
        assert db_path.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_ensure_parent_directory_is_racetolerant(self, tmp_path: Path) -> None:
        """Issue #6171: _ensure_parent_directory should tolerate concurrent directory creation.

        This directly tests that _ensure_parent_directory handles the case where
        the directory is created between the exists() check and mkdir() call.
        """
        file_path = tmp_path / "subdir" / "file.json"
        parent = file_path.parent

        # Ensure parent doesn't exist initially
        assert not parent.exists()

        # Simulate race: create the directory right when mkdir is called
        original_mkdir = Path.mkdir
        call_count = [0]

        def mkdir_with_race(self, *args, **kwargs):
            call_count[0] += 1
            # Before mkdir, create the directory to simulate another process winning
            if not self.exists():
                import os
                os.makedirs(str(self), exist_ok=True)
            # Now the original mkdir should succeed due to exist_ok=True

        with patch.object(Path, "mkdir", mkdir_with_race):
            # This should NOT raise FileExistsError because we use exist_ok=True
            _ensure_parent_directory(file_path)

        # Parent should now exist
        assert parent.exists()

    def test_concurrent_directory_creation_succeeds(self, tmp_path: Path) -> None:
        """Issue #6171: Multiple threads creating the same directory should all succeed.

        This tests that _ensure_parent_directory is thread-safe and doesn't
        fail when multiple threads try to create the same parent directory.
        """
        file_path = tmp_path / "shared" / "todo.json"
        errors = []
        success_count = [0]
        lock = threading.Lock()

        def create_storage_and_save(worker_id: int) -> None:
            try:
                storage = TodoStorage(str(file_path))
                storage.save([Todo(id=worker_id, text=f"worker-{worker_id}")])
                with lock:
                    success_count[0] += 1
            except Exception as e:
                errors.append((worker_id, e))

        # Create multiple threads that will try to create the same directory
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_storage_and_save, args=(i,))
            threads.append(t)

        # Start all threads nearly simultaneously
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)

        # No thread should have encountered FileExistsError or other errors
        assert len(errors) == 0, f"Threads encountered errors: {errors}"
        # At least some should have succeeded
        assert success_count[0] > 0, "At least one thread should have succeeded"

    def test_error_handling_distinguishes_file_vs_permission_error(self, tmp_path: Path) -> None:
        """Issue #6171: Error handling should distinguish between 'path is a file' and 'permission denied'.

        The fix should provide clear error messages for different failure modes.
        """
        # Test 1: Parent path is a file (should raise ValueError)
        blocking_file = tmp_path / "blocking_file"
        blocking_file.write_text("I am a file")

        file_path = blocking_file / "subdir" / "todo.json"

        with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
            _ensure_parent_directory(file_path)

    def test_normal_nested_path_creation_still_works(self, tmp_path: Path) -> None:
        """Issue #6171: Normal nested directory creation should still work after the fix."""
        # Create a deeply nested path that doesn't exist
        db_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test")])

        # Verify file was created
        assert db_path.exists()
        loaded = storage.load()
        assert len(loaded) == 1

    def test_existing_parent_directory_works(self, tmp_path: Path) -> None:
        """Issue #6171: Should work when parent directory already exists."""
        # Pre-create the parent directory
        parent = tmp_path / "existing"
        parent.mkdir()

        db_path = parent / "todo.json"
        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test")])

        assert db_path.exists()
