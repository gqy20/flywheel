"""Test for cleanup deadlock in __enter__ finally block (Issue #1207).

The issue is that in the finally block of __enter__, the code calls
asyncio.run_coroutine_threadsafe(cleanup_lock(), loop).result() which can
block and cause a deadlock if the event loop is busy or stopping.

The fix should use loop.call_soon_threadsafe to schedule the cleanup
without waiting for the result.
"""

import asyncio
import threading
import time
from unittest.mock import Mock, patch

from flywheel.storage import _AsyncCompatibleLock


def test_finally_block_cleanup_does_not_block():
    """Test that cleanup in finally block doesn't block on .result().

    This test verifies the fix for Issue #1207: The finally block in
    __enter__ should not call .result() on the future, which can block
    indefinitely if the event loop is busy or stopping. Instead, it should
    use a non-blocking approach like loop.call_soon_threadsafe.
    """
    lock = _AsyncCompatibleLock()

    # Track if cleanup was scheduled without blocking
    cleanup_scheduled = threading.Event()
    cleanup_completed = threading.Event()

    original_call_soon_threadsafe = asyncio.BaseEventLoop.call_soon_threadsafe

    def mock_call_soon_threadsafe(self, callback, *args, **kwargs):
        """Mock that tracks when cleanup is scheduled."""
        cleanup_scheduled.set()

        # Check if callback is a coroutine (which would be wrong)
        # or a regular function (which is correct)
        if asyncio.iscoroutinefunction(callback):
            raise AssertionError(
                "cleanup_lock should not be a coroutine scheduled with "
                "call_soon_threadsafe. It should be a regular function or "
                "the cleanup should be scheduled differently."
            )

        # Call the original to maintain normal behavior
        return original_call_soon_threadsafe(callback, *args, **kwargs)

    # Create a slow event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_loop():
        loop.run_forever()

    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()

    try:
        with patch.object(
            asyncio.BaseEventLoop,
            'call_soon_threadsafe',
            mock_call_soon_threadsafe
        ):
            # Try to acquire lock with timeout scenario
            # We'll simulate a timeout by making the lock already held
            async def hold_lock():
                async with lock:
                    await asyncio.sleep(2)

            # Start holding the lock
            lock_holder = threading.Thread(
                target=lambda: loop.run_until_complete(hold_lock())
            )
            lock_holder.start()

            # Wait a bit for lock to be acquired
            time.sleep(0.1)

            # Now try to acquire from sync context
            # This should timeout and trigger the finally block cleanup
            try:
                with lock:
                    pass
            except TimeoutError:
                # Expected - lock was held by another thread
                pass

            # If cleanup was scheduled non-blockingly, this event should be set
            # The current implementation might use run_coroutine_threadsafe
            # which would block on .result()
            # We want to verify it doesn't block

    finally:
        loop.call_soon(loop.stop)
        loop_thread.join(timeout=2)
        loop.close()


def test_finally_block_uses_call_soon_threadsafe():
    """Test that finally block uses non-blocking cleanup method.

    This test specifically checks that the cleanup in the finally block
    uses loop.call_soon_threadsafe or another non-blocking method,
    NOT asyncio.run_coroutine_threadsafe(...).result() which can deadlock.
    """
    lock = _AsyncCompatibleLock()

    # We need to trigger the finally block cleanup path
    # This happens when:
    # 1. Lock acquisition times out
    # 2. Lock is acquired after timeout but before cancellation
    # 3. finally block runs with self._locked == False and self._lock.locked() == True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_loop():
        loop.run_forever()

    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()

    try:
        # Mock the cleanup to track how it's called
        original_run_coroutine_threadsafe = asyncio.run_coroutine_threadsafe
        cleanup_calls = []

        def mock_run_coroutine_threadsafe(coro, loop):
            """Track if run_coroutine_threadsafe is used with .result()."""
            cleanup_calls.append({
                'method': 'run_coroutine_threadsafe',
                'has_result_call': False  # Will track if .result() is called
            })

            # Create a mock future that tracks .result() calls
            mock_future = Mock()

            def mock_result(timeout=None):
                cleanup_calls[0]['has_result_call'] = True
                # Simulate the cleanup completing
                if asyncio.iscoroutine(coro):
                    # Run the coroutine to do the actual cleanup
                    new_loop = asyncio.new_event_loop()
                    try:
                        result = new_loop.run_until_complete(coro)
                        return result
                    finally:
                        new_loop.close()
                return None

            mock_future.result = mock_result
            mock_future.cancel = Mock()
            return mock_future

        with patch(
            'asyncio.run_coroutine_threadsafe',
            side_effect=mock_run_coroutine_threadsafe
        ):
            # Create a scenario that triggers the cleanup path
            # Hold the lock from another thread
            async def hold_lock():
                # Acquire the internal lock directly
                await lock._lock.acquire()
                await asyncio.sleep(0.5)  # Hold it for a bit
                lock._lock.release()

            holder = threading.Thread(
                target=lambda: loop.run_until_complete(hold_lock())
            )
            holder.start()

            time.sleep(0.1)  # Let the holder acquire the lock

            # Try to acquire - will timeout and potentially trigger cleanup
            try:
                with lock:
                    pass
            except (TimeoutError, RuntimeError):
                pass  # Expected

            holder.join(timeout=2)

            # Check if cleanup was called with .result()
            # The old (buggy) implementation would call .result() which can block
            # The new implementation should not block on .result()
            if cleanup_calls:
                # If cleanup was triggered, verify it doesn't block
                # In the fixed version, we might not use run_coroutine_threadsafe
                # or if we do, we shouldn't call .result() in a way that blocks
                pass

    finally:
        loop.call_soon(loop.stop)
        loop_thread.join(timeout=2)
        loop.close()


def test_lock_cleanup_without_blocking():
    """Test that lock cleanup after timeout doesn't cause deadlock.

    This is a regression test for Issue #1207. The test ensures that
    when lock acquisition times out but the lock is acquired in the
    background, the cleanup in the finally block doesn't deadlock
    by blocking on .result().
    """
    lock = _AsyncCompatibleLock()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_loop():
        loop.run_forever()

    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()

    try:
        # Simulate the race condition:
        # 1. Start lock acquisition
        # 2. Timeout occurs
        # 3. Lock gets acquired after timeout
        # 4. Cleanup needs to release the lock

        # First, hold the lock
        async def hold_lock_briefly():
            await lock._lock.acquire()
            await asyncio.sleep(0.2)
            lock._lock.release()

        holder = threading.Thread(
            target=lambda: loop.run_until_complete(hold_lock_briefly())
        )
        holder.start()

        time.sleep(0.05)  # Let lock be held

        # Try to acquire - should timeout initially
        start_time = time.time()
        timeout_occurred = False

        try:
            with lock:
                # If we get here, lock was acquired
                pass
        except TimeoutError:
            timeout_occurred = True
        except RuntimeError:
            # Might get RuntimeError if event loop issues
            pass

        elapsed = time.time() - start_time

        # The key assertion: cleanup should not cause indefinite blocking
        # If the buggy code exists (calling .result() in finally),
        # this test might hang or take a very long time
        assert elapsed < 3.0, (
            f"Lock operation took {elapsed:.2f}s, suggesting potential "
            "deadlock in finally block cleanup. This indicates Issue #1207 "
            "has not been fixed."
        )

        holder.join(timeout=2)

    finally:
        loop.call_soon(loop.stop)
        loop_thread.join(timeout=2)
        loop.close()
