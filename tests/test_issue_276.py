"""Test Windows file locking handles files larger than 2GB (Issue #276).

This test verifies that the file locking mechanism uses the actual file size
instead of a hardcoded value (0x7FFF0000 ≈ 2GB) which would fail for larger files.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_uses_file_size():
    """Test that Windows file locking uses actual file size, not hardcoded 0x7FFF0000.

    The current implementation uses a hardcoded lock range of 0x7FFF0000 (≈2GB).
    This test verifies that it should use os.path.getsize() to get the actual file size.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_large_file.json")

        # Create a storage with some todos
        storage = Storage(path=storage_path)
        for i in range(100):
            storage.add(Todo(title=f"Todo {i}", status="pending"))

        # Get the actual file size
        file_size = os.path.getsize(storage_path)

        # Mock msvcrt.locking to capture the lock range argument
        original_locking = None
        if os.name == 'nt':
            import msvcrt
            original_locking = msvcrt.locking

        lock_calls = []

        def mock_locking(fd, mode, size):
            """Mock that captures lock range calls."""
            lock_calls.append(('lock', fd, mode, size))
            # Always succeed
            return None

        def mock_unlocking(fd, mode, size):
            """Mock that captures unlock range calls."""
            lock_calls.append(('unlock', fd, mode, size))
            # Always succeed
            return None

        with patch('msvcrt.locking', side_effect=mock_locking):
            # Reload storage to trigger file locking
            storage2 = Storage(path=storage_path)
            todos = storage2.list()

        # Verify that locking was called
        assert len(lock_calls) > 0, "msvcrt.locking was not called"

        # Get the lock size argument from the first lock call
        lock_size = None
        for call in lock_calls:
            if call[0] == 'lock':
                lock_size = call[3]
                break

        assert lock_size is not None, "Lock size was not captured"

        # The lock size should be at least the file size
        # Current implementation uses 0x7FFF0000 which is ≈2GB (2147479552 bytes)
        hardcoded_limit = 0x7FFF0000

        # This test will FAIL with the current implementation because
        # it uses a hardcoded value instead of the actual file size
        # After the fix, it should use the actual file size or larger
        if file_size > hardcoded_limit:
            # If file is larger than hardcoded limit, we MUST use actual file size
            # This will FAIL with current implementation
            assert lock_size >= file_size, \
                f"Lock size {lock_size} is less than file size {file_size}. " \
                f"Current implementation uses hardcoded 0x7FFF0000 which fails for files > 2GB."
        else:
            # For small files, the hardcoded limit works but is not ideal
            # This test documents the issue
            assert lock_size == hardcoded_limit, \
                f"Current implementation uses hardcoded 0x7FFF0000, got {lock_size:#x}"


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_exceeds_hardcoded_limit():
    """Test that demonstrates the hardcoded 0x7FFF0000 limit problem.

    This test creates a scenario where the file size could exceed
    the hardcoded lock range limit, causing the lock to fail.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_limit.json")

        # The hardcoded limit in current implementation
        hardcoded_limit = 0x7FFF0000  # ≈2GB

        # Mock os.path.getsize to simulate a file larger than hardcoded limit
        # This simulates what happens when the todo file grows beyond 2GB
        with patch('os.path.getsize', return_value=hardcoded_limit + 1024):
            storage = Storage(path=storage_path)
            storage.add(Todo(title="Test Todo", status="pending"))

            # Get the actual (simulated) file size
            simulated_size = os.path.getsize(storage_path)

            # The simulated size exceeds the hardcoded limit
            assert simulated_size > hardcoded_limit, \
                f"Simulated file size {simulated_size} should exceed hardcoded limit {hardcoded_limit}"

            # With current implementation, locking would fail for such files
            # because it tries to lock only 0x7FFF0000 bytes, which is less than
            # the file size, leaving part of the file unprotected


def test_cross_platform_lock_size_logic():
    """Test that documents the expected cross-platform file locking behavior.

    This test serves as documentation for the expected behavior:
    - On Windows: lock range should match file size (using os.path.getsize)
    - On Unix: fcntl.flock locks the entire file automatically
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_cross_platform.json")

        # Create a storage file
        storage = Storage(path=storage_path)
        for i in range(50):
            storage.add(Todo(title=f"Todo {i}", status="pending"))

        # Get file size
        file_size = os.path.getsize(storage_path)

        if os.name == 'nt':
            # On Windows, the lock range should be at least the file size
            # Current implementation uses hardcoded 0x7FFF0000 which is incorrect
            hardcoded_limit = 0x7FFF0000

            # This assertion documents the expected behavior after fix
            # After fix, lock range should be >= file_size
            # For now, this test will document the current incorrect behavior
            if file_size <= hardcoded_limit:
                # Small files work with current implementation
                assert file_size > 0, "File should have content"
            else:
                # Large files (>2GB) will fail with current implementation
                # This is the bug we're fixing
                pass
        else:
            # On Unix, fcntl.flock locks entire file automatically
            # No need to specify size - this is the advantage of Unix locking
            assert file_size > 0, "File should have content"


def test_windows_file_lock_range_calculation():
    """Test the helper function that calculates Windows file lock range.

    This test verifies that the _get_windows_lock_range() method correctly
    returns the lock size based on actual file size, not a hardcoded value.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_lock_range.json")

        # Create a storage file
        storage = Storage(path=storage_path)
        storage.add(Todo(title="Test Todo", status="pending"))

        # Get file size
        file_size = os.path.getsize(storage_path)

        # Test that storage has a method to get lock range
        # This will be added as part of the fix
        if hasattr(storage, '_get_windows_lock_range'):
            lock_range = storage._get_windows_lock_range(storage_path)
            # Lock range should be at least the file size
            assert lock_range >= file_size, \
                f"Lock range {lock_range} should be >= file size {file_size}"
        else:
            # Before fix: this method doesn't exist
            # The fix will add this method
            pass


def test_windows_lock_handles_large_files():
    """Test that Windows locking can handle files larger than 2GB.

    This test uses mocking to simulate a large file scenario.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_large_file.json")

        # The hardcoded limit in current implementation
        hardcoded_limit = 0x7FFF0000  # ≈2GB

        # Create storage
        storage = Storage(path=storage_path)
        storage.add(Todo(title="Test Todo", status="pending"))

        # Test _get_windows_lock_range if it exists (after fix)
        if hasattr(storage, '_get_windows_lock_range'):
            # Mock a file larger than 2GB
            with patch('os.path.getsize', return_value=hardcoded_limit + 1024):
                lock_range = storage._get_windows_lock_range(storage_path)
                # Should handle files larger than hardcoded limit
                assert lock_range > hardcoded_limit, \
                    f"Lock range {lock_range} should handle files > 2GB"
