"""Test for race condition in _get_or_create_loop (Issue #1271).

The issue is that the check `if self._event_loop is not None:` occurs outside
the lock `with self._loop_lock`. While there is a double-check inside, the
logic flow is fragile. Given the complexity of the initialization (creating
threads, loops), it is safer to hold the lock immediately to ensure only one
thread performs the initialization logic.

This test creates a race condition scenario where multiple threads try to
get or create the event loop simultaneously.
"""

import asyncio
import threading
import time
from unittest.mock import patch, MagicMock

from flywheel.storage import _AsyncCompatibleLock


def test_get_or_create_loop_thread_safety():
    """Test that _get_or_create_loop is thread-safe under concurrent access.

    This test verifies the fix for Issue #1271: Multiple threads calling
    _get_or_create_loop simultaneously should not cause race conditions.
    The lock should be held immediately to ensure only one thread performs
    the initialization logic.
    """
    lock = _AsyncCompatibleLock()

    # Track how many times the loop is created
    creation_count = {'count': 0}
    original_new_event_loop = asyncio.new_event_loop

    def mock_new_event_loop():
        """Mock that tracks loop creation."""
        creation_count['count'] += 1
        # Add a small delay to make race conditions more likely
        time.sleep(0.001)
        return original_new_event_loop()

    # Patch asyncio.new_event_loop to track creations
    with patch('asyncio.new_event_loop', side_effect=mock_new_event_loop):
        # Create multiple threads that will all try to get/create the loop
        threads = []
        results = []
        errors = []

        def get_loop_thread():
            """Function to be run in each thread."""
            try:
                loop = lock._get_or_create_loop()
                results.append(loop)
            except Exception as e:
                errors.append(e)

        # Start many threads simultaneously
        num_threads = 10
        for _ in range(num_threads):
            thread = threading.Thread(target=get_loop_thread)
            threads.append(thread)

        # Start all threads at roughly the same time
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)

        # Verify no errors occurred
        assert not errors, f"Errors occurred: {errors}"

        # All threads should have gotten the same loop
        # (it should only be created once)
        assert len(results) == num_threads, (
            f"Expected {num_threads} results, got {len(results)}"
        )

        # All results should be the same loop object
        first_loop = results[0]
        for loop in results[1:]:
            assert loop is first_loop, (
                "Not all threads got the same loop object - this indicates "
                "a race condition in _get_or_create_loop"
            )

        # The loop should only be created once
        # (with the race condition, it might be created multiple times)
        assert creation_count['count'] == 1, (
            f"Event loop was created {creation_count['count']} times, "
            f"expected 1. This indicates a race condition in "
            f"_get_or_create_loop where multiple threads are creating "
            f"loops simultaneously. The check at line 97 occurs outside "
            f"the lock, allowing multiple threads to pass the check and "
            f"enter the lock section, each creating their own loop."
        )


def test_get_or_create_loop_with_simultaneous_calls():
    """Test concurrent calls to _get_or_create_loop don't create multiple loops.

    This is a more aggressive test that tries to maximize the chance of
    triggering the race condition by using barriers to synchronize threads.
    """
    lock = _AsyncCompatibleLock()

    # Track loop creations
    creation_count = {'count': 0}
    original_new_event_loop = asyncio.new_event_loop
    loops_created = []

    def mock_new_event_loop():
        """Mock that tracks loop creation."""
        creation_count['count'] += 1
        loop = original_new_event_loop()
        loops_created.append(loop)
        # Simulate slow initialization
        time.sleep(0.01)
        return loop

    with patch('asyncio.new_event_loop', side_effect=mock_new_event_loop):
        # Use a barrier to synchronize threads
        barrier = threading.Barrier(10)
        threads = []
        results = []
        errors = []

        def get_loop_with_barrier():
            """Function that synchronizes threads before calling _get_or_create_loop."""
            try:
                # Wait for all threads to be ready
                barrier.wait(timeout=5)
                # All threads call _get_or_create_loop simultaneously
                loop = lock._get_or_create_loop()
                results.append(loop)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        num_threads = 10
        for _ in range(num_threads):
            thread = threading.Thread(target=get_loop_with_barrier)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Verify no errors
        assert not errors, f"Errors occurred: {errors}"

        # Verify all threads got the same loop
        assert len(results) == num_threads
        first_loop = results[0]
        for loop in results[1:]:
            assert loop is first_loop, (
                "Threads got different loop objects - race condition detected"
            )

        # Critical assertion: only ONE loop should be created
        # The bug at line 97 allows the race condition:
        # Thread A: if self._event_loop is not None: (passes, it's None)
        # Thread B: if self._event_loop is not None: (passes, it's still None)
        # Thread A: with self._loop_lock:
        # Thread B: with self._loop_lock: (waits)
        # Thread A: creates loop
        # Thread A: exits lock
        # Thread B: enters lock, double-check fails (loop exists now)
        # Thread B: returns the loop
        #
        # BUT if the timing is just right:
        # Thread A: if self._event_loop is not None: (passes, it's None)
        # Thread A: with self._loop_lock:
        # Thread A: double-check if self._event_loop is not None: (passes)
        # Thread A: starts creating loop (slow operation)
        # Thread A: still in lock, creating loop
        # Thread B: if self._event_loop is not None: (passes, it's still None)
        # Thread B: with self._loop_lock: (waits for A)
        # Thread A: finishes creating loop
        # Thread A: exits lock
        # Thread B: enters lock
        # Thread B: double-check if self._event_loop is not None: (FAILS - loop exists)
        # Thread B: returns existing loop
        #
        # So theoretically it should work, but the issue claims this is fragile.
        # The fix is to hold the lock from the beginning.

        assert creation_count['count'] == 1, (
            f"CRITICAL: Event loop was created {creation_count['count']} times!\n"
            f"This confirms the race condition in Issue #1271.\n"
            f"Multiple threads bypassed the initial check outside the lock\n"
            f"and each created their own event loop. The fix should move\n"
            f"the initial check inside the lock or hold the lock immediately."
        )


def test_get_or_create_loop_reuses_cached_loop():
    """Test that _get_or_create_loop properly reuses cached loops.

    This is a basic test to ensure the caching mechanism works correctly.
    """
    lock = _AsyncCompatibleLock()

    # First call should create a loop
    loop1 = lock._get_or_create_loop()
    assert loop1 is not None

    # Second call should return the same loop
    loop2 = lock._get_or_create_loop()
    assert loop1 is loop2, "Should return the same cached loop"

    # Third call should also return the same loop
    loop3 = lock._get_or_create_loop()
    assert loop1 is loop3, "Should return the same cached loop"
