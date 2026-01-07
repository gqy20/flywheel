"""Test for Issue #958: Public classmethod for lock file cleanup on startup."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from flywheel.storage import FileStorage


class TestPublicLockCleanupClassmethod:
    """Test public classmethod for lock file cleanup (Issue #958)."""

    def test_cleanup_stale_locks_classmethod_exists(self):
        """Test that cleanup_stale_locks classmethod exists in FileStorage."""
        # This test will fail until we implement the public classmethod
        assert hasattr(FileStorage, 'cleanup_stale_locks'), \
            "FileStorage should have public cleanup_stale_locks classmethod"

        # Verify it's a classmethod
        method = getattr(FileStorage, 'cleanup_stale_locks')
        assert isinstance(method, classmethod), \
            "cleanup_stale_locks should be a classmethod"

    def test_cleanup_stale_locks_removes_dead_pid_locks(self):
        """Test that cleanup_stale_locks removes lock files with dead PIDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple stale lock files with dead PIDs
            lock_file1 = tmpdir_path / "test1.json.lock"
            lock_file2 = tmpdir_path / "test2.json.lock"

            fake_pid = 99999  # A PID that doesn't exist
            for lock_file in [lock_file1, lock_file2]:
                with open(lock_file, 'w') as f:
                    f.write(f"pid={fake_pid}\n")
                    f.write(f"locked_at={time.time()}\n")

            # Verify lock files exist
            assert lock_file1.exists(), "Lock file 1 should exist before cleanup"
            assert lock_file2.exists(), "Lock file 2 should exist before cleanup"

            # Call the public classmethod to clean up stale locks
            FileStorage.cleanup_stale_locks(tmpdir_path)

            # The stale lock files should be removed
            assert not lock_file1.exists(), "Lock file 1 should be removed after cleanup"
            assert not lock_file2.exists(), "Lock file 2 should be removed after cleanup"

    def test_cleanup_stale_locks_preserves_active_locks(self):
        """Test that cleanup_stale_locks preserves locks from active processes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            lock_file = tmpdir_path / "test.json.lock"

            # Create a lock file with the current process's PID (active)
            current_pid = os.getpid()
            with open(lock_file, 'w') as f:
                f.write(f"pid={current_pid}\n")
                f.write(f"locked_at={time.time()}\n")

            # Verify lock file exists
            assert lock_file.exists(), "Lock file should exist before cleanup"

            # Call cleanup - should preserve active locks
            FileStorage.cleanup_stale_locks(tmpdir_path)

            # The active lock file should NOT be removed
            assert lock_file.exists(), "Active lock file should be preserved"

            # Clean up
            lock_file.unlink()

    def test_cleanup_stale_locks_handles_corrupted_files(self):
        """Test that cleanup_stale_locks handles corrupted lock files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            lock_file = tmpdir_path / "test.json.lock"

            # Create a corrupted lock file
            with open(lock_file, 'w') as f:
                f.write("corrupted content\nno valid pid\n")

            # Verify lock file exists
            assert lock_file.exists(), "Corrupted lock file should exist before cleanup"

            # Call cleanup - should handle corrupted files
            FileStorage.cleanup_stale_locks(tmpdir_path)

            # The corrupted lock file should be removed
            assert not lock_file.exists(), "Corrupted lock file should be removed"

    def test_cleanup_stale_locks_handles_nonexistent_directory(self):
        """Test that cleanup_stale_locks handles nonexistent directory gracefully."""
        nonexistent_path = Path("/nonexistent/directory/path")

        # Should not raise an exception
        FileStorage.cleanup_stale_locks(nonexistent_path)

    def test_cleanup_stale_locks_handles_empty_directory(self):
        """Test that cleanup_stale_locks handles empty directory without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Empty directory, no lock files
            # Should not raise an exception
            FileStorage.cleanup_stale_locks(tmpdir_path)

    def test_cleanup_stale_locks_scans_subdirectories(self):
        """Test that cleanup_stale_locks only processes .lock files in the specified directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a subdirectory with a lock file (should NOT be cleaned up)
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            sub_lock = subdir / "sub.json.lock"
            fake_pid = 99999
            with open(sub_lock, 'w') as f:
                f.write(f"pid={fake_pid}\n")
                f.write(f"locked_at={time.time()}\n")

            # Create a lock file in the main directory (should be cleaned up)
            main_lock = tmpdir_path / "main.json.lock"
            with open(main_lock, 'w') as f:
                f.write(f"pid={fake_pid}\n")
                f.write(f"locked_at={time.time()}\n")

            # Verify both lock files exist
            assert sub_lock.exists(), "Subdirectory lock file should exist"
            assert main_lock.exists(), "Main directory lock file should exist"

            # Call cleanup - should only process files in the specified directory
            FileStorage.cleanup_stale_locks(tmpdir_path)

            # Only the main directory lock file should be removed
            # (not the subdirectory lock file)
            # Note: This depends on implementation - glob("*.lock") only matches
            # files in the specified directory, not subdirectories
            assert not main_lock.exists(), "Main directory lock should be removed"
            # Subdirectory lock should still exist (glob doesn't recurse)
            assert sub_lock.exists(), "Subdirectory lock should not be affected"
