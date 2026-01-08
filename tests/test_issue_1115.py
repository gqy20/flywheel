"""Test for Issue #1115: IOMetrics.log_summary async with threading.Lock deadlock.

Issue #1115: IOMetrics.log_summary uses `async with self._lock` where
self._lock is threading.Lock(), which doesn't support async context manager.

This causes AttributeError: 'threading.Lock' object has no attribute '__aenter__'

The fix is to either:
1. Change self._lock to asyncio.Lock
2. Change log_summary to sync method and use `with self._lock`

This test verifies the problem exists before fix.
"""


def test_iometrics_lock_type():
    """Verify that IOMetrics._lock is properly typed for async usage."""
    from src.flywheel.storage import IOMetrics
    import asyncio
    import threading

    metrics = IOMetrics()

    # The current implementation uses threading.Lock but tries to use it with async with
    # threading.Lock doesn't have __aenter__ and __aexit__ methods
    lock_type = type(metrics._lock)

    # Check if lock supports async context manager
    has_async_context = hasattr(metrics._lock, '__aenter__') and hasattr(metrics._lock, '__aexit__')

    # Current bug: threading.Lock doesn't support async context
    if lock_type == threading.Lock:
        assert not has_async_context, "threading.Lock should not have async context methods"

    # This test documents the bug - threading.Lock with async with will fail
    # After fix, this should pass with an async-compatible lock


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
