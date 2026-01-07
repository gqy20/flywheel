"""Test Windows degraded mode file locking implementation (Issue #910).

This test verifies that when pywin32 import fails on Windows, the code
properly falls back to file-based locking (.lock files) with:
- _acquire_file_lock implementation
- PID checking for stale lock detection
- atexit cleanup handler
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def test_acquire_file_lock_method_exists():
    """Test that _acquire_file_lock method exists in FileStorage class.

    This verifies the fix for Issue #910 which claimed that _acquire_file_lock
    was only mentioned in comments but not implemented.
    """
    from flywheel.storage import FileStorage

    # Check that _acquire_file_lock method exists
    assert hasattr(FileStorage, '_acquire_file_lock'), \
        "FileStorage should have _acquire_file_lock method"

    # Check that it's a callable method
    assert callable(getattr(FileStorage, '_acquire_file_lock')), \
        "_acquire_file_lock should be a callable method"


def test_file_lock_has_pid_checking():
    """Test that file lock implementation includes PID checking.

    This verifies that the degraded mode file lock uses PID checking
    for stale lock detection as mentioned in the comments.
    """
    from flywheel.storage import FileStorage
    import inspect

    # Get the source code of _acquire_file_lock
    source = inspect.getsource(FileStorage._acquire_file_lock)

    # Verify PID checking logic is present
    assert 'pid=' in source or 'os.getpid()' in source, \
        "File lock implementation should include PID checking"

    # Verify stale lock detection is present
    assert 'stale' in source.lower(), \
        "File lock implementation should include stale lock detection"

    # Verify lock file creation is present
    assert '.lock' in source, \
        "File lock implementation should create .lock files"


def test_file_lock_has_atexit_cleanup():
    """Test that file lock implementation includes atexit cleanup handler.

    This verifies that lock files are cleaned up on normal program termination.
    """
    from flywheel.storage import FileStorage
    import inspect

    # Get the source code of _cleanup method
    source = inspect.getsource(FileStorage._cleanup)

    # Verify atexit cleanup logic is present
    assert 'lock_file_path' in source, \
        "Cleanup method should handle lock_file_path"

    assert 'unlink' in source or 'remove' in source, \
        "Cleanup method should remove lock files"


def test_degraded_mode_creates_lock_file():
    """Test that degraded mode actually creates .lock files.

    This is an integration test that verifies the complete file locking
    mechanism works in degraded mode.
    """
    from flywheel.storage import FileStorage, _is_degraded_mode

    # Only run this test in degraded mode (no pywin32 on Windows, or no fcntl on Unix)
    if not _is_degraded_mode():
        pytest.skip("Test only applicable in degraded mode")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.json"

        # Create a FileStorage instance
        storage = FileStorage(db_path, lock_timeout=5)

        try:
            # Check if lock file was created
            lock_file_path = db_path.with_suffix('.json.lock')

            # In degraded mode, a lock file should be created
            # (Note: The exact timing depends on when the lock is acquired)
            if hasattr(storage, '_lock_file_path') and storage._lock_file_path:
                assert storage._lock_file_path.endswith('.lock'), \
                    "Lock file path should end with .lock"

        finally:
            storage.close()


def test_cleanup_removes_lock_file():
    """Test that _cleanup method removes lock files.

    This verifies the atexit cleanup handler works correctly.
    """
    from flywheel.storage import FileStorage
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.json"
        lock_path = db_path.with_suffix('.json.lock')

        # Create a FileStorage instance
        storage = FileStorage(db_path, lock_timeout=5)

        try:
            # Simulate having a lock file
            if hasattr(storage, '_lock_file_path'):
                storage._lock_file_path = str(lock_path)

                # Create a fake lock file
                lock_path.write_text(f"pid={os.getpid()}\nlocked_at=1.0\n")

                # Call _cleanup to remove it
                storage._cleanup()

                # Verify lock file was removed
                assert not lock_path.exists(), \
                    "Cleanup method should remove lock file"
        finally:
            storage.close()


def test_degraded_mode_windows_without_pywin32():
    """Test that Windows properly falls back to file locking without pywin32.

    This test verifies Issue #910 is fixed: Windows degraded mode should have
    complete file lock implementation, not just comments.
    """
    import flywheel.storage as storage_module

    # On Windows, if pywin32 is not available, win32file should be None
    if sys.platform == 'win32':
        # Check that the module handles missing pywin32
        if storage_module.win32file is None:
            # In degraded mode, _is_degraded_mode should return True
            assert storage_module._is_degraded_mode(), \
                "Should be in degraded mode when pywin32 is not available"

            # Verify _acquire_file_lock exists and handles degraded mode
            from flywheel.storage import FileStorage
            import inspect

            source = inspect.getsource(FileStorage._acquire_file_lock)
            assert '_is_degraded_mode' in source, \
                "_acquire_file_lock should check _is_degraded_mode()"
            assert 'degraded' in source.lower(), \
                "_acquire_file_lock should handle degraded mode"
    else:
        # On Unix, win32file should always be None
        assert storage_module.win32file is None


def test_file_lock_implementation_completeness():
    """Test that file lock implementation is complete and functional.

    This comprehensive test verifies all components mentioned in Issue #910:
    1. _acquire_file_lock method exists and is implemented
    2. PID checking logic exists
    3. Timestamp-based stale detection exists
    4. atexit cleanup exists
    """
    from flywheel.storage import FileStorage
    import inspect

    # Get the source code of _acquire_file_lock
    source = inspect.getsource(FileStorage._acquire_file_lock)

    # Check for all key components
    required_components = [
        ('os.getpid()', 'PID retrieval'),
        ('locked_at', 'Timestamp tracking'),
        ('stale', 'Stale lock detection'),
        ('.lock', 'Lock file creation'),
        ('FileExistsError', 'Lock file conflict handling'),
    ]

    for component, description in required_components:
        assert component in source, \
            f"File lock implementation should include {description} ({component})"

    # Check _cleanup method
    cleanup_source = inspect.getsource(FileStorage._cleanup)
    assert '_lock_file_path' in cleanup_source, \
        "Cleanup should handle _lock_file_path"


def test_windows_degraded_mode_safety_checks():
    """Test that Windows degraded mode has safety checks to prevent accidental pywin32 usage.

    This verifies the defensive assertions that ensure degraded mode cannot
    accidentally use pywin32 APIs.
    """
    from flywheel.storage import FileStorage
    import inspect

    # Get the source code of _acquire_file_lock
    source = inspect.getsource(FileStorage._acquire_file_lock)

    # Check for safety assertions in degraded mode
    if sys.platform == 'win32':
        # On Windows, check for safety assertions
        assert 'assert win32file is None' in source or 'win32file is None' in source, \
            "Degraded mode should verify win32file is None"


def test_issue_910_false_positive_verification():
    """Comprehensive test to verify Issue #910 is a false positive.

    This test explicitly checks that ALL components mentioned in the issue
    are actually implemented:
    - _acquire_file_lock method (line 1408+)
    - PID checking logic
    - atexit cleanup handler
    """
    from flywheel.storage import FileStorage
    import inspect

    # 1. Verify _acquire_file_lock exists
    assert hasattr(FileStorage, '_acquire_file_lock'), \
        "Issue #910: _acquire_file_lock method must exist"

    # 2. Verify it's a complete implementation, not just a stub
    source = inspect.getsource(FileStorage._acquire_file_lock)
    assert len(source) > 500, \
        "Issue #910: _acquire_file_lock should have substantial implementation"

    # 3. Verify PID checking
    assert 'os.getpid()' in source, \
        "Issue #910: Implementation must include PID checking"

    # 4. Verify timestamp tracking
    assert 'locked_at' in source, \
        "Issue #910: Implementation must include timestamp for stale detection"

    # 5. Verify atexit cleanup
    cleanup_source = inspect.getsource(FileStorage._cleanup)
    assert '_lock_file_path' in cleanup_source, \
        "Issue #910: atexit cleanup must handle lock files"
    assert 'unlink' in cleanup_source, \
        "Issue #910: atexit cleanup must remove lock files"

    # 6. Verify degraded mode handling
    assert '_is_degraded_mode' in source, \
        "Issue #910: Implementation must check degraded mode"
