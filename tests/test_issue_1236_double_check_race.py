"""Tests for issue #1236 - Race condition in double-check logic.

The issue is that when asyncio.get_running_loop() raises RuntimeError (no running loop),
the code has a double-check pattern, but it doesn't properly return the existing loop
when another thread has already created one. This can cause multiple loops to be created,
violating the mutual exclusion principle.
"""
import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1236DoubleCheckRace:
    """Test that the double-check in _get_or_create_loop properly returns existing loops."""

    def test_double_check_returns_existing_loop(self):
        """Test that double-check properly returns existing loop instead of creating new one.

        This test simulates the race condition described in issue #1236:
        1. Thread 1 fails to get running loop (RuntimeError)
        2. Thread 1 waits to acquire _loop_lock
        3. Thread 2 acquires _loop_lock first and creates a loop
        4. Thread 1 acquires _loop_lock and should return Thread 2's loop
        5. BUG: Thread 1 ignores the double-check and creates its own loop
        """
        lock = _AsyncCompatibleLock()
        loops = []
        exceptions = []

        # Thread 1: Will try to get/create loop
        def thread1_create_loop():
            """Thread 1: Try to create a loop."""
            try:
                # This should either get existing loop or create new one
                # But due to the bug, it might create a second loop
                loop = lock._get_or_create_loop()
                loops.append(("thread1", id(loop), loop))
            except Exception as e:
                exceptions.append(("thread1", e))

        # Thread 2: Will also try to get/create loop
        def thread2_create_loop():
            """Thread 2: Try to create a loop."""
            try:
                time.sleep(0.001)  # Small delay to create race condition
                loop = lock._get_or_create_loop()
                loops.append(("thread2", id(loop), loop))
            except Exception as e:
                exceptions.append(("thread2", e))

        # Start both threads
        t1 = threading.Thread(target=thread1_create_loop)
        t2 = threading.Thread(target=thread2_create_loop)

        t1.start()
        t2.start()

        # Wait for completion
        t1.join(timeout=5)
        t2.join(timeout=5)

        # No exceptions should have occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # Both threads should get the SAME loop instance
        # This is the key assertion: the double-check should prevent creating a second loop
        assert len(loops) == 2, f"Expected 2 loop entries, got {len(loops)}"

        thread1_loop_id = loops[0][1]
        thread2_loop_id = loops[1][1]

        assert thread1_loop_id == thread2_loop_id, (
            f"Race condition detected: Thread 1 got loop {thread1_loop_id}, "
            f"Thread 2 got loop {thread2_loop_id}. "
            "The double-check should ensure both threads get the same loop instance."
        )

    def test_multiple_threads_single_loop_instance(self):
        """Test that multiple threads all get the same loop instance.

        This is a stronger test with more threads to stress test the double-check logic.
        """
        lock = _AsyncCompatibleLock()
        loops = []
        exceptions = []

        def get_loop(thread_id):
            """Get loop from a thread."""
            try:
                time.sleep(0.0001 * thread_id)  # Stagger the starts
                loop = lock._get_or_create_loop()
                loops.append((thread_id, id(loop)))
            except Exception as e:
                exceptions.append((thread_id, e))

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=get_loop, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)

        # No exceptions
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # All threads should have gotten a loop
        assert len(loops) == 10, f"Expected 10 loops, got {len(loops)}"

        # All loop IDs should be the same
        loop_ids = [loop_id for _, loop_id in loops]
        unique_ids = set(loop_ids)

        assert len(unique_ids) == 1, (
            f"Expected all threads to get the same loop instance, "
            f"but got {len(unique_ids)} different loop instances: {unique_ids}. "
            "This indicates the double-check logic is not working correctly."
        )

    def test_loop_reuse_after_initial_creation(self):
        """Test that once a loop is created, subsequent calls return the same loop.

        This test verifies that the double-check logic works correctly even when
        called from the same thread multiple times.
        """
        lock = _AsyncCompatibleLock()

        # First call creates the loop
        loop1 = lock._get_or_create_loop()
        assert loop1 is not None

        # Second call should return the same loop
        loop2 = lock._get_or_create_loop()
        assert loop1 is loop2, "Subsequent calls should return the same loop instance"

        # Third call from another thread should also return the same loop
        loops_other_thread = []

        def get_loop_from_other_thread():
            """Get loop from a different thread."""
            loop = lock._get_or_create_loop()
            loops_other_thread.append(loop)

        t = threading.Thread(target=get_loop_from_other_thread)
        t.start()
        t.join(timeout=5)

        assert len(loops_other_thread) == 1
        assert loop1 is loops_other_thread[0], (
            "Different thread should get the same loop instance"
        )
