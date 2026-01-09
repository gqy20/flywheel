"""Test for Issue #1171: asyncio.Lock.release() should be called directly.

Issue #1171: In `__exit__`, the code uses `asyncio.run_coroutine_threadsafe`
to call `self._lock.release()`, but `asyncio.Lock.release()` is a synchronous
method, not a coroutine. This should be called directly.
"""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_lock_release_is_sync_not_async():
    """Test that Lock.release() is synchronous, not a coroutine."""
    lock = _AsyncCompatibleLock()

    # Verify that lock._lock.release() is NOT a coroutine function
    release_method = lock._lock.release
    assert not asyncio.iscoroutinefunction(release_method), (
        "asyncio.Lock.release() should be a synchronous method, not a coroutine"
    )

    # Verify it's a regular method
    assert callable(release_method), "release() should be callable"


def test_sync_context_manager_basic():
    """Test that sync context manager works correctly."""
    lock = _AsyncCompatibleLock()

    # This should not raise any exceptions
    with lock:
        # Lock is held here
        assert lock._lock.locked(), "Lock should be held inside context"

    # Lock should be released after exiting context
    assert not lock._lock.locked(), "Lock should be released after context exit"


def test_multiple_sync_acquisitions():
    """Test multiple sequential acquisitions."""
    lock = _AsyncCompatibleLock()

    for i in range(5):
        with lock:
            assert lock._lock.locked(), f"Lock should be held in iteration {i}"
        assert not lock._lock.locked(), f"Lock should be released after iteration {i}"


def test_threaded_sync_context():
    """Test sync context manager from multiple threads."""
    lock = _AsyncCompatibleLock()
    results = []
    errors = []

    def worker(thread_id):
        try:
            for i in range(3):
                with lock:
                    # Simulate some work
                    time.sleep(0.01)
                    results.append(f"thread-{thread_id}-iter-{i}")
        except Exception as e:
            errors.append((thread_id, e))

    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"No errors should occur, but got: {errors}"
    assert len(results) == 9, f"Should have 9 results, got {len(results)}"


def test_mixed_sync_and_async():
    """Test that sync and async contexts can both use the lock."""
    lock = _AsyncCompatibleLock()
    results = []

    async def async_worker():
        async with lock:
            results.append("async")
            await asyncio.sleep(0.01)

    def sync_worker():
        with lock:
            results.append("sync")
            time.sleep(0.01)

    # Run async worker
    asyncio.run(async_worker())

    # Run sync worker
    sync_worker()

    assert len(results) == 2
    assert "async" in results
    assert "sync" in results


def test_release_without_acquire_raises():
    """Test that releasing an unlocked lock raises RuntimeError."""
    lock = _AsyncCompatibleLock()

    # Try to release without acquiring
    # This should raise RuntimeError
    try:
        lock._lock.release()
        assert False, "Releasing unlocked lock should raise RuntimeError"
    except RuntimeError:
        pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
