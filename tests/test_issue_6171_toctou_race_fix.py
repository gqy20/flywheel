"""Regression tests for issue #6171: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition between checking if parent exists (line 43) and calling mkdir (line 45).
An attacker could create a file/directory at 'parent' path between the check and mkdir,
causing mkdir to fail or behave unexpectedly.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


class TestTOCTOURaceCondition:
    """Tests for TOCTOU race condition in _ensure_parent_directory."""

    def test_toctou_race_directory_exists_before_mkdir(self, tmp_path) -> None:
        """Issue #6171: mkdir should succeed even if parent dir already exists.

        This directly tests the TOCTOU race scenario:
        - Directory exists at the time mkdir is called
        - mkdir with exist_ok=False would fail
        - mkdir with exist_ok=True succeeds

        Before fix: raises FileExistsError wrapped in OSError
        After fix: succeeds without error
        """
        db_path = tmp_path / "subdir" / "todo.json"
        parent_dir = db_path.parent

        # Pre-create the parent directory to simulate TOCTOU race
        # (directory created between exists() check and mkdir() call)
        parent_dir.mkdir(parents=True, exist_ok=True)

        # This should NOT raise an error even though directory already exists
        # The fix should use exist_ok=True
        _ensure_parent_directory(db_path)

        # Verify the directory still exists
        assert parent_dir.exists(), "Parent directory should exist after _ensure_parent_directory"

    def test_toctou_race_file_created_at_parent_path(self, tmp_path) -> None:
        """Issue #6171: Should raise clear error if file (not dir) created at parent path during race.

        This simulates a more malicious race where an attacker creates a FILE at the
        parent path between our check and mkdir.
        """
        db_path = tmp_path / "blocked" / "todo.json"
        parent_dir = db_path.parent

        # Create a FILE at the parent path to simulate malicious race
        parent_dir.write_text("attacker content")

        # Should raise a clear error about file vs directory
        # This tests that mkdir on a file path fails appropriately
        # ValueError is raised because the code checks if parent path is a file
        with pytest.raises((OSError, ValueError), match=r"(directory|not a directory|File exists|Not a directory|exists as a file)"):
            _ensure_parent_directory(db_path)

    def test_concurrent_calls_to_ensure_parent_directory(self, tmp_path) -> None:
        """Issue #6171: Multiple threads calling _ensure_parent_directory concurrently should all succeed.

        This is a more realistic test of the race condition with actual concurrent access.
        """
        errors = []
        success_count = [0]
        barrier = threading.Barrier(10)  # Synchronize all threads

        def call_ensure_parent(thread_id):
            """Call _ensure_parent_directory and track results."""
            try:
                # Wait for all threads to be ready
                barrier.wait()
                # All threads try to create the same parent directory
                thread_db_path = tmp_path / "concurrent" / "todo.json"
                _ensure_parent_directory(thread_db_path)
                success_count[0] += 1
            except FileExistsError as e:
                # This is the specific error we're trying to fix
                errors.append(f"FileExistsError: {e}")
            except OSError as e:
                # On some systems this might be wrapped in OSError
                if "File exists" in str(e):
                    errors.append(f"OSError (FileExists): {e}")
                else:
                    errors.append(f"OSError: {e}")
            except Exception as e:
                errors.append(f"{type(e).__name__}: {e}")

        # Create multiple threads that all try to create directories concurrently
        threads = []
        for i in range(10):
            t = threading.Thread(target=call_ensure_parent, args=(i,))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All threads should succeed (no FileExistsError from race)
        assert len(errors) == 0, f"Unexpected errors (TOCTOU race not fixed): {errors}"
        assert success_count[0] == 10, "All threads should succeed"

    def test_storage_save_succeeds_with_concurrent_directory_creation(self, tmp_path) -> None:
        """Issue #6171: TodoStorage.save() should work even with concurrent directory creation."""
        db_path = tmp_path / "race" / "todo.json"
        parent_dir = db_path.parent

        # Pre-create the directory to simulate race
        parent_dir.mkdir(parents=True, exist_ok=True)

        storage = TodoStorage(str(db_path))

        # This should succeed, not raise FileExistsError
        storage.save([])

        # Verify the data was saved
        assert db_path.exists(), "Database file should be created"

    def test_mkdir_with_exist_ok_true_succeeds_for_existing_directory(self, tmp_path) -> None:
        """Baseline test: mkdir with exist_ok=True should not fail for existing directory."""
        parent_dir = tmp_path / "existing"
        parent_dir.mkdir(parents=True, exist_ok=True)

        # Calling mkdir again with exist_ok=True should succeed
        parent_dir.mkdir(parents=True, exist_ok=True)

        # But with exist_ok=False, it would fail
        with pytest.raises(FileExistsError):
            parent_dir.mkdir(parents=True, exist_ok=False)

    def test_ensure_parent_directory_with_existing_directory(self, tmp_path) -> None:
        """Test that _ensure_parent_directory works with already existing directory."""
        db_path = tmp_path / "existing_dir" / "todo.json"
        parent_dir = db_path.parent

        # Pre-create the directory
        parent_dir.mkdir(parents=True, exist_ok=True)

        # This should succeed without raising FileExistsError
        _ensure_parent_directory(db_path)

        assert parent_dir.exists()

    def test_storage_save_creates_parent_directory(self, tmp_path) -> None:
        """Test that TodoStorage.save() properly creates parent directories."""
        from flywheel.todo import Todo

        db_path = tmp_path / "new" / "nested" / "dir" / "todo.json"
        parent_dir = db_path.parent

        # Parent should not exist yet
        assert not parent_dir.exists()

        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test", done=False)])

        # Now parent should exist
        assert parent_dir.exists()
        assert db_path.exists()

    def test_error_message_clarity_for_file_at_parent_path(self, tmp_path) -> None:
        """Issue #6171: Error message should clearly indicate the problem when a file blocks directory creation."""
        db_path = tmp_path / "file_block" / "todo.json"
        parent_dir = db_path.parent

        # Create a file at the parent path
        parent_dir.write_text("I am a file")

        # Should raise with a clear error message
        with pytest.raises(ValueError) as exc_info:
            _ensure_parent_directory(db_path)

        # Check that error message is helpful
        error_msg = str(exc_info.value)
        assert "file" in error_msg.lower() or "not a directory" in error_msg.lower()
        assert str(parent_dir) in error_msg or "blocked" in error_msg

    def test_mkdir_exist_ok_false_fails_for_existing_dir(self, tmp_path) -> None:
        """Baseline: Demonstrate that exist_ok=False fails for existing directory.

        This test documents the exact behavior that causes the TOCTOU vulnerability.
        """
        parent_dir = tmp_path / "test_dir"
        parent_dir.mkdir(parents=True, exist_ok=True)

        # mkdir with exist_ok=False fails when directory exists
        with pytest.raises(FileExistsError):
            parent_dir.mkdir(parents=True, exist_ok=False)
