"""Test for issue #1351: Unsafe fallback in _AsyncCompatibleLock._get_async_lock

This test verifies that calling _get_async_lock() without a running event loop
raises a clear error instead of calling asyncio.get_event_loop(), which can
create a new event loop that is never closed and is not running.
"""
import asyncio
import threading
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_get_async_lock_without_running_loop_in_thread():
    """Test that _get_async_lock raises error when called from thread without running loop.

    This test creates a new thread (which has no running event loop) and attempts
    to call _get_async_lock(). The old implementation would call
    asyncio.get_event_loop() which creates a new event loop that is never closed.
    The new implementation should raise a clear RuntimeError instead.
    """
    lock = _AsyncCompatibleLock()
    error_raised = False
    error_message = ""

    def try_get_async_lock():
        nonlocal error_raised, error_message
        try:
            # This should raise RuntimeError since there's no running loop
            lock._get_async_lock()
        except RuntimeError as e:
            error_raised = True
            error_message = str(e)
        except Exception as e:
            error_raised = True
            error_message = f"Unexpected error: {type(e).__name__}: {e}"

    thread = threading.Thread(target=try_get_async_lock)
    thread.start()
    thread.join(timeout=5)

    # Assert that an error was raised
    assert error_raised, "Expected RuntimeError to be raised when calling _get_async_lock without a running loop"

    # Assert that the error message is clear and helpful
    assert "running event loop" in error_message.lower() or "async context" in error_message.lower(), \
        f"Expected error message to mention 'running event loop' or 'async context', got: {error_message}"


def test_get_async_lock_with_running_loop():
    """Test that _get_async_lock works correctly when called with a running loop.

    This is a positive test case to verify the normal operation still works.
    """
    async def test_with_running_loop():
        lock = _AsyncCompatibleLock()
        # This should work fine since we're in an async context with a running loop
        async_lock = lock._get_async_lock()
        assert async_lock is not None
        assert isinstance(async_lock, asyncio.Lock)

    # Run the async function in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_with_running_loop())
    finally:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
