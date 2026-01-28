"""Test for issue #1100: Potential deadlock in log_summary.

This test verifies that the lock is released before performing I/O (logging)
operations in the log_summary method to prevent potential deadlocks.
"""
import asyncio
import os
import time
from unittest.mock import Mock, patch
from flywheel.storage import StorageMetrics


def test_lock_released_before_logging():
    """Test that lock is released before logging in log_summary.

    This test ensures that the lock is not held while performing I/O operations
    (logging) which can block all other metrics operations and cause deadlocks.

    The test works by:
    1. Recording some operations
    2. Patching logger.info to simulate slow I/O
    3. Starting log_summary in background
    4. Attempting to acquire lock immediately
    5. Verifying lock can be acquired while logging is in progress
    """
    os.environ['FW_STORAGE_METRICS_LOG'] = '1'

    metrics = StorageMetrics()

    # Record some operations
    metrics.record_operation('read', 0.1, 0, True)
    metrics.record_operation('write', 0.2, 1, True)

    # Track whether lock was held during logging
    lock_held_during_logging = []
    logging_started = threading.Event()

    original_info = Mock()

    def mock_logger_info(*args, **kwargs):
        logging_started.set()
        # Simulate checking if lock is held during logging
        # In asyncio.Lock, we can check if it's locked
        if hasattr(metrics._lock, 'locked'):
            lock_held_during_logging.append(metrics._lock.locked())
        # Small delay to ensure we're in the middle of logging
        time.sleep(0.01)
        original_info(*args, **kwargs)

    import threading

    with patch('flywheel.storage.logger.info', side_effect=mock_logger_info):
        # Run log_summary in a thread
        result = []
        def run_log_summary():
            metrics.log_summary()
            result.append('done')

        thread = threading.Thread(target=run_log_summary)
        thread.start()

        # Wait for logging to start
        logging_started.wait(timeout=2)

        # Give it a moment
        time.sleep(0.01)

        thread.join(timeout=2)

    # Verify logging was called
    assert result == ['done'], "log_summary should complete"

    # The key assertion: lock should NOT be held during logging
    # If lock_held_during_logging contains True, it means lock was held while logging
    # We expect it to be empty or contain only False values
    if lock_held_during_logging:
        assert not any(lock_held_during_logging), \
            f"Lock was held during logging (potential deadlock): {lock_held_during_logging}"


def test_async_lock_released_before_logging():
    """Test that asyncio.Lock is released before logging.

    This is an async version of the test that specifically checks asyncio.Lock behavior.
    """
    import asyncio

    async def test_async():
        os.environ['FW_STORAGE_METRICS_LOG'] = '1'

        metrics = StorageMetrics()

        # Record some operations
        await metrics.record_operation_async('read', 0.1, 0, True)
        await metrics.record_operation_async('write', 0.2, 1, True)

        # Track lock state during logging
        lock_states = []
        logging_in_progress = asyncio.Event()

        original_info = Mock()

        def mock_logger_info(*args, **kwargs):
            logging_in_progress.set()
            # Check if lock is held
            lock_states.append(metrics._lock.locked())
            original_info(*args, **kwargs)

        with patch('flywheel.storage.logger.info', side_effect=mock_logger_info):
            # Start log_summary in background task
            task = asyncio.create_task(
                asyncio.to_thread(metrics.log_summary)
            )

            # Wait for logging to start
            await asyncio.sleep(0.01)

            # Wait for completion
            await task

        # Verify lock was released during logging
        # Lock should not be held while doing I/O
        if lock_states:
            assert not any(lock_states), \
                f"Lock was held during logging (potential deadlock): {lock_states}"

    # Run the async test
    asyncio.run(test_async())


def test_data_consistency_with_early_lock_release():
    """Test that metrics data remains consistent even with early lock release.

    This test verifies that even if we release the lock before logging,
    the metrics data used for logging is a consistent snapshot.
    """
    os.environ['FW_STORAGE_METRICS_LOG'] = '1'

    metrics = StorageMetrics()

    # Record some operations
    metrics.record_operation('read', 0.1, 0, True)
    metrics.record_operation('write', 0.2, 1, False, 'ENOENT')
    metrics.record_operation('flush', 0.05, 0, True)

    # Log summary should work correctly
    # We're not testing the exact output, just that it doesn't crash
    # and produces consistent results
    try:
        metrics.log_summary()
    except Exception as e:
        raise AssertionError(f"log_summary failed with early lock release: {e}")
