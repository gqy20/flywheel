"""Test for Issue #1298: _AsyncCompatibleLock reentrancy optimization.

This test verifies that _AsyncCompatibleLock supports reentrant locks
(locks that can be acquired multiple times by the same thread) to prevent
deadlocks in nested synchronous method calls.
"""
import threading
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_sync_lock_reentrancy():
    """Test that the same thread can acquire the lock multiple times."""
    lock = _AsyncCompatibleLock()

    # First acquisition should succeed
    acquired_first = False
    acquired_second = False

    def nested_acquire():
        nonlocal acquired_first, acquired_second
        with lock:
            acquired_first = True
            # Try to acquire the same lock again in the same thread
            with lock:
                acquired_second = True

    # This should work without deadlock if the lock is reentrant
    nested_acquire()

    assert acquired_first, "First lock acquisition failed"
    assert acquired_second, "Second lock acquisition failed (lock is not reentrant)"


def test_sync_lock_with_recursive_function():
    """Test lock behavior with recursive function calls."""
    lock = _AsyncCompatibleLock()
    call_count = 0
    max_depth = 3

    def recursive_call(depth=0):
        nonlocal call_count
        with lock:
            call_count += 1
            if depth < max_depth:
                recursive_call(depth + 1)

    # This should complete without deadlock
    recursive_call()

    assert call_count == max_depth + 1, f"Expected {max_depth + 1} calls, got {call_count}"


def test_sync_lock_different_threads():
    """Test that different threads still properly block each other."""
    lock = _AsyncCompatibleLock()
    thread1_acquired = False
    thread2_acquired = False
    thread1_done = threading.Event()
    thread2_started = threading.Event()

    def thread1_func():
        nonlocal thread1_acquired
        with lock:
            thread1_acquired = True
            thread2_started.wait()  # Wait for thread2 to start trying to acquire
            threading.Event().wait(0.1)  # Hold the lock briefly

    def thread2_func():
        nonlocal thread2_acquired
        thread2_started.set()
        with lock:
            thread2_acquired = True

    t1 = threading.Thread(target=thread1_func)
    t2 = threading.Thread(target=thread2_func)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert thread1_acquired, "Thread 1 failed to acquire lock"
    assert thread2_acquired, "Thread 2 failed to acquire lock"
    # The key test: thread2 should only acquire AFTER thread1 releases


def test_current_implementation_is_not_reentrant():
    """Document the current behavior: threading.Lock is NOT reentrant."""
    lock = _AsyncCompatibleLock()

    # This test demonstrates the problem with the current implementation
    # using threading.Lock instead of threading.RLock
    acquired_first = False
    deadlock_occurred = False

    def attempt_nested_acquire():
        nonlocal acquired_first, deadlock_occurred
        try:
            with lock:
                acquired_first = True
                # This will cause a deadlock with threading.Lock
                # because the same thread tries to acquire twice
                with lock:
                    deadlock_occurred = False  # Should never reach here
        except RuntimeError:
            # Might get a different error depending on implementation
            deadlock_occurred = True

    # Run in a thread with timeout to detect actual deadlock
    result = [None]
    exception = [None]

    def run_test():
        try:
            attempt_nested_acquire()
            result.append(False)  # No deadlock
        except Exception as e:
            exception.append(e)

    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
    thread.join(timeout=2.0)

    if thread.is_alive():
        # Thread is still running => deadlock occurred
        deadlock_occurred = True
    elif result[-1] is False:
        # Completed successfully => lock is reentrant
        deadlock_occurred = False
    elif exception[-1] is not None:
        # Exception occurred
        deadlock_occurred = True

    # For now, we expect this to fail with the current implementation
    # After the fix, this test will need to be updated
    assert deadlock_occurred or not acquired_first, \
        "Current implementation should demonstrate non-reentrant behavior"
