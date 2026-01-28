"""Test for deadlock when reusing running event loop (Issue #1235)."""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_deadlock_when_reusing_running_loop():
    """Test that reusing a running event loop from another thread causes deadlock.

    This test verifies the bug described in Issue #1235: When _get_or_create_loop
    detects a running event loop in the current thread, it assigns it directly to
    self._event_loop. If this lock is subsequently used by another thread (without
    a running loop) in a synchronous manner (using 'with'), run_coroutine_threadsafe
    will try to submit tasks to the first thread's loop. If the first thread is
    blocked waiting for that task to complete, and that task needs to execute in
    the first thread, a deadlock occurs.

    The test creates:
    1. Thread A with a running event loop
    2. Lock created in Thread A (which reuses Thread A's loop)
    3. Thread B tries to acquire the lock synchronously
    4. Thread A tries to acquire the same lock
    5. Deadlock occurs because Thread B's task is submitted to Thread A's loop,
       but Thread A is blocked waiting for the lock

    The fix should ensure that locks cannot reuse running event loops unless
    it's guaranteed that the lock will only be used within that thread.
    """
    # Track what happened
    results = {
        "thread_a_started": False,
        "thread_b_started": False,
        "thread_a_finished": False,
        "thread_b_finished": False,
        "lock_acquired_in_thread_a": False,
        "lock_acquired_in_thread_b": False,
        "error": None,
    }

    lock = None
    deadlock_detected = threading.Event()

    def thread_a_with_loop():
        """Thread A: Has a running event loop and creates the lock."""
        nonlocal lock

        results["thread_a_started"] = True

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the loop
            loop.run_until_complete(_thread_a_async_task(results))
        except Exception as e:
            results["error"] = f"Thread A error: {e}"
        finally:
            loop.close()
            results["thread_a_finished"] = True

    async def _thread_a_async_task(results):
        """Async task in Thread A."""
        nonlocal lock

        # Create the lock while the loop is running
        # This will cause the lock to reuse this thread's event loop
        lock = _AsyncCompatibleLock()

        # Verify the lock is using this thread's event loop
        assert lock._event_loop is not None, "Lock should have an event loop"
        assert lock._event_loop_thread_id == threading.get_ident(), (
            f"Lock should use Thread A's loop, but uses thread {lock._event_loop_thread_id}"
        )

        # Signal that Thread A is ready
        results["thread_a_started"] = True

        # Give Thread B time to start and try to acquire the lock
        await asyncio.sleep(0.5)

        # Now try to acquire the lock in Thread A
        # This will deadlock because Thread B's task is pending in Thread A's loop,
        # but Thread A is waiting for the lock
        try:
            # Use asyncio timeout to detect deadlock
            await asyncio.wait_for(lock.__aenter__(), timeout=1.0)
            results["lock_acquired_in_thread_a"] = True
            await lock.__aexit__(None, None, None)
        except asyncio.TimeoutError:
            # Deadlock detected!
            deadlock_detected.set()
            results["error"] = "Deadlock detected in Thread A"

    def thread_b_without_loop():
        """Thread B: No running loop, tries to use the lock synchronously."""
        results["thread_b_started"] = True

        # Wait a bit to ensure Thread A has created the lock
        time.sleep(0.1)

        try:
            # Try to acquire the lock synchronously
            # This will submit a task to Thread A's event loop
            # If Thread A is waiting for this lock, we get a deadlock
            with lock:
                results["lock_acquired_in_thread_b"] = True
                # Hold the lock briefly
                time.sleep(0.1)
        except Exception as e:
            results["error"] = f"Thread B error: {e}"
        finally:
            results["thread_b_finished"] = True

    # Start both threads
    thread_a = threading.Thread(target=thread_a_with_loop)
    thread_b = threading.Thread(target=thread_b_without_loop)

    thread_a.start()
    time.sleep(0.1)  # Ensure Thread A starts first and creates the lock
    thread_b.start()

    # Wait for deadlock detection or completion (with timeout)
    deadlock_detected.wait(timeout=5.0)

    # Wait for threads with timeout
    thread_a.join(timeout=2.0)
    thread_b.join(timeout=2.0)

    # Check results
    assert results["thread_a_started"], "Thread A should have started"
    assert results["thread_b_started"], "Thread B should have started"

    # The bug: either deadlock occurred, or one thread couldn't acquire the lock
    if deadlock_detected.is_set():
        # This is the bug - deadlock occurred
        assert False, (
            "DEADLOCK DETECTED! This is the bug from Issue #1235: "
            "The lock reused Thread A's event loop, then Thread B tried to use it "
            "synchronously, submitting a task to Thread A's loop. But Thread A was "
            "blocked waiting for the lock, causing a deadlock."
        )

    # Alternative failure: Thread B finished but Thread A is stuck
    if results["thread_b_finished"] and not results["thread_a_finished"]:
        assert False, (
            "Thread A is stuck (likely deadlocked)! This is the bug from Issue #1235."
        )

    # If we get here without deadlock, the bug might be fixed
    # But we should verify both threads completed successfully
    # Note: This might still fail if the deadlock has a different manifestation


def test_lock_should_not_reuse_running_loop_from_other_context():
    """Test that a lock creates its own dedicated event loop.

    This test verifies the fix for Issue #1235: when a lock is created in a
    context with a running event loop, it should create its own dedicated
    event loop in a separate thread, rather than reusing the running loop.
    This prevents deadlocks when the lock is used from other threads.
    """
    # Create an event loop and run it
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    lock_created = threading.Event()

    async def create_lock_in_async_context():
        """Create a lock while the event loop is running."""
        lock = _AsyncCompatibleLock()

        # Check if the lock is using this thread's event loop
        current_thread_id = threading.get_ident()

        if lock._event_loop is not None:
            if lock._event_loop_thread_id == current_thread_id:
                # BUG: The lock is reusing the running event loop
                lock_created.set()
                lock_created.lock_reused_running_loop = True
            else:
                # GOOD: The lock created its own event loop in another thread
                lock_created.set()
                lock_created.lock_reused_running_loop = False

    # Run the async function
    loop.run_until_complete(create_lock_in_async_context())

    # Wait for the lock to be created
    lock_created.wait(timeout=2.0)
    assert lock_created.is_set(), "Lock should have been created"

    # After the fix: the lock should NOT reuse the running event loop
    if hasattr(lock_created, "lock_reused_running_loop"):
        assert not lock_created.lock_reused_running_loop, (
            "FIX VERIFIED: The lock correctly created its own dedicated event loop "
            "in a separate thread, preventing the deadlock described in Issue #1235."
        )

    loop.close()
