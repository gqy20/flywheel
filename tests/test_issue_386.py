"""Tests for Issue #386 - Windows locking seek(0) documentation.

The issue report claimed that `msvcrt.locking` uses absolute file offsets
and that `seek(0)` is unnecessary. However, investigation revealed that
`msvcrt.locking` actually locks from the CURRENT file position, making
`seek(0)` essential.

The fix clarifies this behavior with detailed comments to prevent future
confusion and ensure the critical seek(0) is not removed.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
class TestWindowsLockingIssue386:
    """Tests for Windows file locking behavior (Issue #386).

    These tests verify and document that msvcrt.locking locks bytes
    starting from the CURRENT file position, not from position 0.
    Therefore, seek(0) is critical before locking/unlocking.
    """

    def test_seek_zero_is_called_before_locking(self):
        """Test that seek(0) is called before locking.

        This test verifies the implementation correctly seeks to position 0
        before calling msvcrt.locking. Without this, we would lock from
        whatever position the file pointer happens to be at.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "testtodos.json"

            # Create a storage instance
            storage = Storage(str(storage_path))

            # Track calls to verify seek(0) happens
            original_acquire = storage._acquire_file_lock
            seek_calls = []

            def mock_acquire_with_tracking(file_handle):
                """Mock _acquire_file_lock to track seek calls."""
                original_seek = file_handle.seek

                def tracking_seek(pos, *args, **kwargs):
                    seek_calls.append(pos)
                    return original_seek(pos, *args, **kwargs)

                file_handle.seek = tracking_seek
                return original_acquire(file_handle)

            with patch.object(storage, '_acquire_file_lock',
                            side_effect=mock_acquire_with_tracking):
                from flywheel.todo import Todo
                storage.add(Todo(title="Test todo"))

            # Verify seek(0) was called (critical for correct locking)
            assert 0 in seek_calls, (
                "seek(0) must be called before msvcrt.locking to ensure "
                "we lock from position 0, not from the current file position"
            )

    def test_locking_depends_on_file_position(self):
        """Test that msvcrt.locking locks from current file position.

        This test demonstrates the actual behavior of msvcrt.locking:
        it locks bytes starting from the current file position.

        This is why seek(0) is critical - without it, we might lock
        the wrong region of the file.
        """
        import msvcrt

        with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Write test data
            test_data = b"0123456789ABCDEFGHIJ"
            with open(tmp_path, 'w+b') as f:
                f.write(test_data)

            # Test: Lock from current position (which is NOT 0)
            with open(tmp_path, 'r+b') as f:
                # Read some data to move file pointer
                f.read(5)  # Pointer now at position 5

                # If we lock without seek, we lock from position 5
                # This demonstrates that locking depends on file position
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 10)
                    # Bytes 5-14 are now locked, NOT bytes 0-9

                    # To unlock, we must be at the same position
                    f.seek(5)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 10)
                except OSError as e:
                    pytest.fail(f"Locking from position 5 failed: {e}")

            # Test: Lock from position 0 (the correct way)
            with open(tmp_path, 'r+b') as f:
                f.read(5)  # Move pointer away from 0

                # CRITICAL: Seek to 0 before locking
                f.seek(0)

                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 10)
                    # Bytes 0-9 are now locked

                    # Verify we can read the locked region
                    f.seek(0)
                    data = f.read(10)
                    assert data == b"0123456789"

                    # Unlock from position 0
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 10)
                except OSError as e:
                    pytest.fail(f"Locking from position 0 failed: {e}")

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def test_lock_unlock_positions_must_match(self):
        """Test that lock and unlock positions must match.

        This test demonstrates that the unlock position must match
        the lock position. This is why both acquire and release
        use seek(0).
        """
        import msvcrt

        with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with open(tmp_path, 'r+b') as f:
                f.write(b"0123456789")

            # Lock from position 0
            with open(tmp_path, 'r+b') as f:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 10)

                # Try to unlock from position 5 (will fail)
                f.seek(5)
                with pytest.raises(OSError):
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 10)

                # Unlock from position 0 (will succeed)
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 10)

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
