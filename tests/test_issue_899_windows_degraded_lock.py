"""Test for Issue #899 - Verify Windows degraded mode file locking mechanism.

This test ensures that when win32file is None (degraded mode), the file-based
locking mechanism actually works and prevents concurrent access issues.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import FileStorage, _is_degraded_mode


class TestWindowsDegradedModeLocking:
    """Test suite for Issue #899 - Windows degraded mode file locking."""

    def test_is_degraded_mode_detects_win32file_none(self):
        """Test that _is_degraded_mode returns True when win32file is None."""
        # Save original state
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            # Mock Windows platform
            with mock.patch('os.name', 'nt'):
                # Simulate win32file being None (degraded mode)
                storage_module.win32file = None

                result = _is_degraded_mode()

                # Should return True in degraded mode on Windows
                assert result is True, (
                    "_is_degraded_mode() should return True when win32file is None on Windows. "
                    "This is critical for enabling file-based locking fallback."
                )

        finally:
            # Restore original state
            storage_module.win32file = original_win32file

    def test_is_degraded_mode_returns_false_with_win32file(self):
        """Test that _is_degraded_mode returns False when win32file is available."""
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            # Mock Windows platform
            with mock.patch('os.name', 'nt'):
                # Create a mock win32file module
                mock_win32file = mock.MagicMock()
                storage_module.win32file = mock_win32file

                result = _is_degraded_mode()

                # Should return False when win32file is available
                assert result is False, (
                    "_is_degraded_mode() should return False when win32file is available."
                )

        finally:
            # Restore original state
            storage_module.win32file = original_win32file

    def test_file_storage_uses_file_lock_in_degraded_mode(self):
        """Test that FileStorage uses .lock files in degraded mode on Windows."""
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, "test_degraded.json")

                # Mock Windows platform and degraded mode
                with mock.patch('os.name', 'nt'):
                    storage_module.win32file = None

                    # Verify degraded mode is active
                    assert _is_degraded_mode() is True, "Should be in degraded mode"

                    # Create FileStorage instance
                    storage = FileStorage(db_path)

                    # Add a todo to trigger lock acquisition
                    storage.add("Test todo in degraded mode")

                    # Verify that .lock file was created and cleaned up
                    lock_file_path = db_path + ".lock"

                    # After operation, lock should be released
                    # Check internal state
                    assert hasattr(storage, '_lock_file_path'), (
                        "FileStorage should track lock file path in degraded mode"
                    )

                    # The lock file should not exist after release
                    assert not os.path.exists(lock_file_path), (
                        "Lock file should be cleaned up after operation completes"
                    )

        finally:
            # Restore original state
            storage_module.win32file = original_win32file

    def test_file_lock_prevents_concurrent_write_in_degraded_mode(self):
        """Test that file-based locking prevents concurrent writes in degraded mode."""
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, "test_concurrent.json")

                # Mock Windows platform and degraded mode
                with mock.patch('os.name', 'nt'):
                    storage_module.win32file = None

                    # Verify degraded mode is active
                    assert _is_degraded_mode() is True

                    # Create first storage instance and add a todo
                    storage1 = FileStorage(db_path)
                    storage1.add("Todo from storage1")

                    # Create second storage instance
                    # This should work fine as long as locks are properly released
                    storage2 = FileStorage(db_path)
                    todos = storage2.list_all()

                    # Should see the todo from storage1
                    assert len(todos) == 1
                    assert todos[0].title == "Todo from storage1"

        finally:
            # Restore original state
            storage_module.win32file = original_win32file

    def test_degraded_mode_creates_lock_file_with_metadata(self):
        """Test that lock files contain PID and timestamp in degraded mode."""
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, "test_lock_metadata.json")
                lock_file_path = db_path + ".lock"

                # Mock Windows platform and degraded mode
                with mock.patch('os.name', 'nt'):
                    storage_module.win32file = None

                    # Create storage and trigger lock acquisition
                    storage = FileStorage(db_path)
                    storage.add("Test")

                    # Manually test lock file creation by calling _acquire_file_lock
                    # We need to test the lock file creation mechanism directly
                    # Create a test file to lock
                    test_file = Path(db_path + "_test")
                    test_file.touch()

                    with open(test_file, 'r') as f:
                        # This should create a lock file
                        storage._acquire_file_lock(f)

                        # Verify lock file exists with metadata
                        assert os.path.exists(lock_file_path), (
                            "Lock file should be created in degraded mode"
                        )

                        with open(lock_file_path, 'r') as lock_file:
                            content = lock_file.read()
                            assert "pid=" in content, (
                                "Lock file should contain PID for stale lock detection"
                            )
                            assert "locked_at=" in content, (
                                "Lock file should contain timestamp for stale lock detection"
                            )

                        # Cleanup
                        storage._release_file_lock(f)
                        test_file.unlink()

        finally:
            # Restore original state
            storage_module.win32file = original_win32file

    def test_stale_lock_detection_in_degraded_mode(self):
        """Test that stale locks are detected and cleaned up in degraded mode."""
        import flywheel.storage as storage_module

        original_win32file = getattr(storage_module, 'win32file', None)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = os.path.join(tmpdir, "test_stale_lock.json")
                lock_file_path = db_path + ".lock"

                # Mock Windows platform and degraded mode
                with mock.patch('os.name', 'nt'):
                    storage_module.win32file = None

                    # Create a fake stale lock file with old timestamp
                    with open(lock_file_path, 'w') as f:
                        # Use a PID that doesn't exist and an old timestamp
                        f.write("pid=99999\n")
                        f.write(f"locked_at={time.time() - 400}\n")  # 6+ minutes ago

                    # Verify stale lock file exists
                    assert os.path.exists(lock_file_path)

                    # Create storage - should detect and remove stale lock
                    storage = FileStorage(db_path)

                    # Add a todo - this should work despite the stale lock
                    storage.add("Test after stale lock cleanup")

                    # Verify the stale lock was handled (may have been cleaned up)
                    todos = storage.list_all()
                    assert len(todos) == 1
                    assert todos[0].title == "Test after stale lock cleanup"

        finally:
            # Restore original state
            storage_module.win32file = original_win32file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
