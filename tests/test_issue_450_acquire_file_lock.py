"""Tests for _acquire_file_lock method completeness (Issue #450).

This test verifies that the _acquire_file_lock method is fully implemented
on both Windows and Unix-like systems.

Issue #450 reported that the _acquire_file_lock method was incomplete with
code truncated at the Windows locking comment. This test verifies that the
method is now fully implemented with:
- Windows: win32file.LockFileEx for mandatory locking with timeout/retry
- Unix: fcntl.flock with timeout/retry
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestAcquireFileLockCompleteness:
    """Test _acquire_file_lock method implementation completeness."""

    def test_method_exists(self):
        """Test that _acquire_file_lock method exists."""
        from flywheel.storage import Storage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify method exists
            assert hasattr(storage, '_acquire_file_lock')
            assert callable(storage._acquire_file_lock)

            storage.close()

    def test_method_has_implementation_on_windows(self):
        """Test that _acquire_file_lock has proper implementation on Windows."""
        from flywheel.storage import Storage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a mock file handle
            mock_file = Mock()
            mock_file.fileno.return_value = 1
            mock_file.name = str(storage_path)

            if os.name == 'nt':
                # On Windows, verify it uses win32file.LockFileEx
                with patch('flywheel.storage.win32file') as mock_win32file, \
                     patch('flywheel.storage.pywintypes') as mock_pywintypes, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time.time to return controlled values
                    mock_time.time.side_effect = [0, 0.1]

                    # Mock successful lock acquisition
                    mock_win32file._get_osfhandle.return_value = 1
                    mock_win32con = Mock()
                    mock_win32con.LOCKFILE_FAIL_IMMEDIATELY = 1
                    mock_win32con.LOCKFILE_EXCLUSIVE_LOCK = 2
                    mock_win32file.LockFileEx.return_value = None

                    # Mock OVERLAPPED structure
                    mock_overlapped = Mock()
                    mock_pywintypes.OVERLAPPED.return_value = mock_overlapped

                    storage = Storage(str(storage_path))

                    # Call _acquire_file_lock - should not raise
                    storage._acquire_file_lock(mock_file)

                    # Verify win32file.LockFileEx was called
                    assert mock_win32file.LockFileEx.called, (
                        "On Windows, _acquire_file_lock should use win32file.LockFileEx "
                        "for mandatory locking"
                    )

                    storage.close()
            else:
                # On Unix, verify it uses fcntl.flock
                with patch('flywheel.storage.fcntl') as mock_fcntl, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time.time to return controlled values
                    mock_time.time.side_effect = [0, 0.1]

                    # Mock successful lock acquisition
                    mock_fcntl.flock.return_value = None

                    storage = Storage(str(storage_path))

                    # Call _acquire_file_lock - should not raise
                    storage._acquire_file_lock(mock_file)

                    # Verify fcntl.flock was called with LOCK_EX | LOCK_NB
                    assert mock_fcntl.flock.called, (
                        "On Unix, _acquire_file_lock should use fcntl.flock"
                    )

                    storage.close()

    def test_method_handles_timeout(self):
        """Test that _acquire_file_lock implements timeout mechanism."""
        from flywheel.storage import Storage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a mock file handle
            mock_file = Mock()
            mock_file.fileno.return_value = 1
            mock_file.name = "test.json"

            if os.name == 'nt':
                # On Windows, test timeout behavior
                with patch('flywheel.storage.win32file') as mock_win32file, \
                     patch('flywheel.storage.pywintypes') as mock_pywintypes, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time progression to trigger timeout
                    mock_time.time.side_effect = [0, 10, 20, 30, 31]
                    mock_time.sleep.return_value = None

                    # Mock lock acquisition failure (lock is held)
                    mock_win32file._get_osfhandle.return_value = 1
                    mock_win32con = Mock()
                    mock_win32con.LOCKFILE_FAIL_IMMEDIATELY = 1
                    mock_win32con.LOCKFILE_EXCLUSIVE_LOCK = 2

                    # Create pywintypes.error for lock violation
                    mock_error = Mock()
                    mock_error.winerror = 33  # ERROR_LOCK_VIOLATION
                    mock_pywintypes.error = type('pywintypes_error', (Exception,), {
                        '__init__': Exception.__init__
                    })

                    def raise_lock_error(*args, **kwargs):
                        error = mock_pywintypes.error()
                        error.winerror = 33
                        raise error

                    mock_win32file.LockFileEx.side_effect = raise_lock_error
                    mock_pywintypes.OVERLAPPED.return_value = Mock()

                    storage = Storage(str(storage_path))

                    # Should raise RuntimeError due to timeout
                    with pytest.raises(RuntimeError) as exc_info:
                        storage._acquire_file_lock(mock_file)

                    assert "timed out" in str(exc_info.value).lower()

                    storage.close()
            else:
                # On Unix, test timeout behavior
                with patch('flywheel.storage.fcntl') as mock_fcntl, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time progression to trigger timeout
                    mock_time.time.side_effect = [0, 10, 20, 30, 31]
                    mock_time.sleep.return_value = None

                    # Mock lock acquisition failure
                    mock_fcntl.flock.side_effect = IOError("Lock held")

                    storage = Storage(str(storage_path))

                    # Should raise RuntimeError due to timeout
                    with pytest.raises(RuntimeError) as exc_info:
                        storage._acquire_file_lock(mock_file)

                    assert "timed out" in str(exc_info.value).lower()

                    storage.close()

    def test_method_implements_retry_logic(self):
        """Test that _acquire_file_lock implements retry logic with exponential backoff."""
        from flywheel.storage import Storage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Create a mock file handle
            mock_file = Mock()
            mock_file.fileno.return_value = 1
            mock_file.name = "test.json"

            if os.name == 'nt':
                # On Windows, test retry logic
                with patch('flywheel.storage.win32file') as mock_win32file, \
                     patch('flywheel.storage.pywintypes') as mock_pywintypes, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time for short delays
                    mock_time.time.side_effect = [0, 0.05, 0.15]
                    mock_time.sleep.return_value = None

                    # Mock lock acquisition failures then success
                    call_count = [0]

                    mock_win32file._get_osfhandle.return_value = 1
                    mock_win32con = Mock()
                    mock_win32con.LOCKFILE_FAIL_IMMEDIATELY = 1
                    mock_win32con.LOCKFILE_EXCLUSIVE_LOCK = 2

                    # Create pywintypes.error for lock violation
                    mock_pywintypes.error = type('pywintypes_error', (Exception,), {
                        '__init__': Exception.__init__
                    })

                    def raise_lock_error_then_succeed(*args, **kwargs):
                        call_count[0] += 1
                        if call_count[0] < 3:
                            error = mock_pywintypes.error()
                            error.winerror = 33
                            raise error
                        return None  # Success on third try

                    mock_win32file.LockFileEx.side_effect = raise_lock_error_then_succeed
                    mock_pywintypes.OVERLAPPED.return_value = Mock()

                    storage = Storage(str(storage_path))

                    # Should succeed after retries
                    storage._acquire_file_lock(mock_file)

                    # Verify multiple attempts were made
                    assert call_count[0] == 3, "Should retry on lock failure"

                    # Verify sleep was called for retry delay
                    assert mock_time.sleep.called, "Should implement retry delay"

                    storage.close()
            else:
                # On Unix, test retry logic
                with patch('flywheel.storage.fcntl') as mock_fcntl, \
                     patch('flywheel.storage.time') as mock_time:

                    # Mock time for short delays
                    mock_time.time.side_effect = [0, 0.05, 0.15]
                    mock_time.sleep.return_value = None

                    # Mock lock acquisition failures then success
                    call_count = [0]

                    def raise_ioerror_then_succeed(*args, **kwargs):
                        call_count[0] += 1
                        if call_count[0] < 3:
                            raise IOError("Lock held")
                        return None  # Success on third try

                    mock_fcntl.flock.side_effect = raise_ioerror_then_succeed

                    storage = Storage(str(storage_path))

                    # Should succeed after retries
                    storage._acquire_file_lock(mock_file)

                    # Verify multiple attempts were made
                    assert call_count[0] == 3, "Should retry on lock failure"

                    # Verify sleep was called for retry delay
                    assert mock_time.sleep.called, "Should implement retry delay"

                    storage.close()

    def test_windows_uses_mandatory_locking_not_msvcrt(self):
        """Test that Windows uses win32file.LockFileEx not msvcrt.locking.

        This is the key fix for Issue #450 - the implementation should use
        win32file.LockFileEx for mandatory locking, not the older msvcrt.locking.
        """
        from flywheel.storage import Storage
        import inspect

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            if os.name == 'nt':
                # Get the source code of _acquire_file_lock
                source = inspect.getsource(storage._acquire_file_lock)

                # Verify it uses win32file.LockFileEx
                assert 'win32file.LockFileEx' in source, (
                    "Windows implementation should use win32file.LockFileEx "
                    "for mandatory locking, not msvcrt.locking"
                )

                # Verify it does NOT use msvcrt.locking (the old incomplete approach)
                assert 'msvcrt.locking' not in source, (
                    "Windows implementation should NOT use msvcrt.locking. "
                    "It should use win32file.LockFileEx for mandatory locking."
                )

                # Verify it implements timeout
                assert '_lock_timeout' in source or 'timeout' in source.lower(), (
                    "Windows implementation should include timeout mechanism"
                )

                # Verify it implements retry logic
                assert 'retry' in source.lower() or 'while' in source.lower(), (
                    "Windows implementation should include retry logic"
                )

            storage.close()

    def test_unix_uses_fcntl_flock(self):
        """Test that Unix uses fcntl.flock."""
        from flywheel.storage import Storage
        import inspect

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            if os.name != 'nt':
                # Get the source code of _acquire_file_lock
                source = inspect.getsource(storage._acquire_file_lock)

                # Verify it uses fcntl.flock
                assert 'fcntl.flock' in source, (
                    "Unix implementation should use fcntl.flock"
                )

                # Verify it uses LOCK_EX | LOCK_NB flags
                assert 'LOCK_EX' in source and 'LOCK_NB' in source, (
                    "Unix implementation should use LOCK_EX | LOCK_NB for non-blocking exclusive lock"
                )

                # Verify it implements timeout
                assert '_lock_timeout' in source or 'timeout' in source.lower(), (
                    "Unix implementation should include timeout mechanism"
                )

                # Verify it implements retry logic
                assert 'retry' in source.lower() or 'while' in source.lower(), (
                    "Unix implementation should include retry logic"
                )

            storage.close()

    def test_method_is_not_truncated(self):
        """Test that _acquire_file_lock method is complete and not truncated.

        This directly addresses Issue #450 which reported the method was
        truncated at the Windows locking comment.
        """
        from flywheel.storage import Storage
        import inspect

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Get the source code
            source = inspect.getsource(storage._acquire_file_lock)

            # Check for incomplete patterns from Issue #450
            incomplete_patterns = [
                '# Windows locking: msvcrt.locking (Is',  # The truncated comment from issue
                'msvcrt.locking (Is',  # Incomplete comment
                '...',  # Incomplete implementation marker
                '# TODO',  # Unimplemented feature marker
                '# FIXME',  # Unimplemented fix marker
                'NotImplementedError',  # Placeholder for unimplemented code
                'pass$',  # Empty implementation (standalone pass)
            ]

            source_lines = source.split('\n')
            for pattern in incomplete_patterns:
                # Check each line for the pattern
                for line in source_lines:
                    if pattern in line:
                        # Allow 'pass' in comments or as part of other statements
                        if pattern == 'pass$':
                            import re
                            if re.search(r'^\s*pass\s*$', line.strip()):
                                pytest.fail(
                                    f"_acquire_file_lock appears to be incomplete. "
                                    f"Found standalone 'pass' statement indicating "
                                    f"unimplemented code: {line}"
                                )
                        else:
                            pytest.fail(
                                f"_acquire_file_lock appears to be incomplete. "
                                f"Found pattern '{pattern}' which suggests "
                                f"truncated or unimplemented code: {line}"
                            )

            # Verify method has actual implementation (not just comments)
            # by checking for key implementation elements
            has_implementation = False

            if os.name == 'nt':
                # Windows implementation markers
                if 'win32file.LockFileEx' in source:
                    has_implementation = True
            else:
                # Unix implementation markers
                if 'fcntl.flock' in source:
                    has_implementation = True

            assert has_implementation, (
                "_acquire_file_lock appears to have no implementation. "
                "Expected platform-specific locking code not found."
            )

            storage.close()
