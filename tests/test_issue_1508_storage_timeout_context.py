"""Test for issue #1508: Add context to StorageTimeoutError

This test verifies that StorageTimeoutError includes useful debugging context
such as timeout duration, operation type, and caller information.
"""

import pytest
import threading
import time
from pathlib import Path

from flywheel.storage import StorageTimeoutError, Storage


def test_storage_timeout_error_includes_timeout_context():
    """Test that StorageTimeoutError from lock acquisition includes timeout context."""
    storage_dir = Path("/tmp/test_issue_1508")
    storage_dir.mkdir(exist_ok=True)

    try:
        storage = Storage(str(storage_dir))

        # Acquire lock in first thread
        lock1 = storage._lock
        lock1.acquire()

        # Try to acquire in second thread with very short timeout
        storage2 = Storage(str(storage_dir))
        storage2._lock_timeout = 0.01  # 10ms timeout

        with pytest.raises(StorageTimeoutError) as exc_info:
            storage2._lock.__enter__()

        error_msg = str(exc_info.value)

        # Verify error message contains timeout information
        assert "0.01" in error_msg or "10ms" in error_msg or "10 ms" in error_msg, \
            f"Error message should contain timeout value: {error_msg}"

        # Verify error message mentions retry attempts
        assert "attempt" in error_msg.lower(), \
            f"Error message should mention retry attempts: {error_msg}"

        lock1.release()

    finally:
        import shutil
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_storage_timeout_error_from_io_operation_includes_timeout():
    """Test that StorageTimeoutError from I/O operations includes timeout context."""
    storage_dir = Path("/tmp/test_issue_1508_io")
    storage_dir.mkdir(exist_ok=True)

    try:
        storage = Storage(str(storage_dir))
        storage._io_timeout = 0.001  # Very short timeout

        # Create a file that will take longer than timeout to read
        test_file = storage_dir / "test.txt"

        # This should timeout and raise StorageTimeoutError
        # We'll use a custom operation that simulates slow I/O
        import asyncio

        async def slow_operation():
            await asyncio.sleep(1)  # Sleep longer than timeout
            return "done"

        with pytest.raises(StorageTimeoutError) as exc_info:
            asyncio.run(storage._execute_io_with_metrics(
                slow_operation,
                operation_type="test_read",
                timeout=storage._io_timeout,
                metrics=None
            ))

        error_msg = str(exc_info.value)

        # Verify error message contains timeout information
        assert "0.001" in error_msg or "1ms" in error_msg or "1 ms" in error_msg, \
            f"Error message should contain timeout value: {error_msg}"

        # Verify error message mentions I/O operation
        assert "I/O" in error_msg or "operation" in error_msg.lower(), \
            f"Error message should mention I/O operation: {error_msg}"

    finally:
        import shutil
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_storage_timeout_error_accepts_optional_parameters():
    """Test that StorageTimeoutError can be constructed with optional context parameters."""
    # Test creating with timeout parameter
    error1 = StorageTimeoutError(
        "Test error",
        timeout=5.0
    )
    assert "5.0" in str(error1) or "5" in str(error1)

    # Test creating with operation parameter
    error2 = StorageTimeoutError(
        "Test error",
        operation="load_cache"
    )
    assert "load_cache" in str(error2)

    # Test creating with caller parameter
    error3 = StorageTimeoutError(
        "Test error",
        caller="test_function"
    )
    assert "test_function" in str(error3)

    # Test creating with all parameters
    error4 = StorageTimeoutError(
        "Test error",
        timeout=10.0,
        operation="save_data",
        caller="main"
    )
    msg = str(error4)
    assert "10.0" in msg or "10" in msg
    assert "save_data" in msg
    assert "main" in msg
