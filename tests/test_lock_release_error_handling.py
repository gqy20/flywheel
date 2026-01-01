"""Test file lock release error handling (Issue #376)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from flywheel.storage import Storage


class TestLockReleaseErrorHandling:
    """Test that _release_file_lock properly handles errors (Issue #376)."""

    def test_release_lock_raises_on_windows_lock_failure(self):
        """Test that _release_file_lock raises IOError on Windows when locking fails."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        # Create a temporary storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = Storage(str(storage_path))

            # Create a mock file handle
            mock_file = MagicMock()

            # Mock msvcrt.locking to raise IOError on release
            with patch('flywheel.storage.msvcrt.locking') as mock_locking:
                mock_locking.side_effect = [
                    None,  # First call (acquire) succeeds
                    IOError(33, "Lock violation"),  # Second call (release) fails
                ]

                # Acquire the lock
                storage._acquire_file_lock(mock_file)

                # Attempting to release should raise IOError
                with pytest.raises(IOError, match="Lock violation"):
                    storage._release_file_lock(mock_file)

    def test_release_lock_raises_on_unix_lock_failure(self):
        """Test that _release_file_lock raises IOError on Unix when locking fails."""
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        # Create a temporary storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = Storage(str(storage_path))

            # Create a mock file handle
            mock_file = MagicMock()
            mock_file.fileno.return_value = 1

            # Mock fcntl.flock to raise IOError on release
            with patch('flywheel.storage.fcntl.flock') as mock_flock:
                mock_flock.side_effect = [
                    None,  # First call (acquire) succeeds
                    IOError("Lock violation"),  # Second call (release) fails
                ]

                # Acquire the lock
                storage._acquire_file_lock(mock_file)

                # Attempting to release should raise IOError
                with pytest.raises(IOError, match="Lock violation"):
                    storage._release_file_lock(mock_file)

    def test_acquire_and_release_lock_consistency(self):
        """Test that acquire and release have consistent error handling.

        This test verifies that both _acquire_file_lock and _release_file_lock
        raise exceptions on error, ensuring consistent error handling behavior.
        """
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        # Create a temporary storage
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = Storage(str(storage_path))

            # Create a mock file handle
            mock_file = MagicMock()
            mock_file.fileno.return_value = 1

            # Mock fcntl.flock to raise IOError on both acquire and release
            with patch('flywheel.storage.fcntl.flock') as mock_flock:
                mock_flock.side_effect = IOError("Lock error")

                # Both acquire and release should raise IOError
                with pytest.raises(IOError, match="Lock error"):
                    storage._acquire_file_lock(mock_file)

                with pytest.raises(IOError, match="Lock error"):
                    storage._release_file_lock(mock_file)
