"""Test for issue #1139: IOMetrics.record_operation uses asyncio.Lock in sync context.

This test verifies that IOMetrics does not use asyncio.Lock in its __init__ method,
which can cause RuntimeError in threads without a running event loop.
"""

import threading
import time
from flywheel.storage import IOMetrics


def test_iometrics_no_asyncio_lock_in_init():
    """Test that IOMetrics can be instantiated in a thread without event loop.

    This test creates IOMetrics in a separate thread that has no event loop.
    If IOMetrics.__init__ uses asyncio.Lock(), this will fail with RuntimeError.
    """
    result = []
    exception = []

    def create_metrics_in_thread():
        """Create IOMetrics instance in a thread without event loop."""
        try:
            metrics = IOMetrics()
            # Verify that the instance was created successfully
            result.append(True)
            # Verify that _lock attribute is NOT an asyncio.Lock
            import asyncio
            assert not isinstance(metrics._lock, asyncio.Lock), (
                "IOMetrics._lock should not be asyncio.Lock in sync context"
            )
            result.append(True)
        except Exception as e:
            exception.append(e)

    # Create and start thread
    thread = threading.Thread(target=create_metrics_in_thread)
    thread.start()
    thread.join(timeout=5)

    # Check results
    assert thread.is_alive() == False, "Thread did not complete"
    assert len(exception) == 0, f"Exception occurred: {exception[0] if exception else 'Unknown'}"
    assert len(result) == 2, "IOMetrics creation or check failed in thread"


def test_iometrics_sync_lock_type():
    """Test that IOMetrics._sync_lock is a threading.Lock."""
    metrics = IOMetrics()

    import threading
    assert isinstance(metrics._sync_lock, threading.Lock), (
        "IOMetrics._sync_lock should be threading.Lock"
    )


def test_iometrics_record_operation_in_thread():
    """Test that record_operation works in a thread without event loop."""
    result = []
    exception = []

    def record_in_thread():
        """Call record_operation in a thread without event loop."""
        try:
            metrics = IOMetrics()
            metrics.record_operation('read', 0.1, 0, True)
            result.append(True)
        except Exception as e:
            exception.append(e)

    thread = threading.Thread(target=record_in_thread)
    thread.start()
    thread.join(timeout=5)

    assert thread.is_alive() == False, "Thread did not complete"
    assert len(exception) == 0, f"Exception occurred: {exception[0] if exception else 'Unknown'}"
    assert len(result) == 1, "record_operation failed in thread"


if __name__ == '__main__':
    test_iometrics_no_asyncio_lock_in_init()
    test_iometrics_sync_lock_type()
    test_iometrics_record_operation_in_thread()
    print("All tests passed!")
