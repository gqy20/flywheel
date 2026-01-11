"""
Test for Issue #1361: Race condition in _get_async_lock with WeakValueDictionary.

The issue is that even with double-check locking inside _async_lock_init_lock,
the WeakValueDictionary's get() method could return None due to garbage collection
between the check and the return statement. This test demonstrates the issue and
verifies the fix.
"""

import asyncio
import gc
import threading
import time
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestWeakValueRaceCondition:
    """Test for race condition in WeakValueDictionary-based lock management."""

    @pytest.mark.asyncio
    async def test_get_async_lock_returns_valid_lock(self):
        """
        Test that _get_async_lock always returns a valid lock.

        This test verifies that the function handles the case where
        WeakValueDictionary.get() returns None due to garbage collection.
        """
        lock = _AsyncCompatibleLock()

        # First call should create and return a lock
        lock1 = lock._get_async_lock()
        assert lock1 is not None
        assert isinstance(lock1, asyncio.Lock)

        # Second call should return the same lock (fast path)
        lock2 = lock._get_async_lock()
        assert lock2 is lock1

    @pytest.mark.asyncio
    async def test_get_async_lock_after_gc(self):
        """
        Test that _get_async_lock works correctly after garbage collection.

        This test simulates the scenario where the lock object is garbage
        collected while stored in WeakValueDictionary.
        """
        lock = _AsyncCompatibleLock()
        current_loop = asyncio.get_running_loop()

        # Create initial lock
        lock1 = lock._get_async_lock()
        assert lock1 is not None

        # Get the weakref to verify GC behavior
        weak_lock = weakref.ref(lock1)

        # Force removal from WeakValueDictionary by deleting our strong reference
        # and triggering GC (in a controlled scenario)
        # In practice, we're testing that the function handles missing locks gracefully
        del lock1
        gc.collect()

        # The weakref should be gone if GC collected it
        # But the function should still work and create a new lock if needed
        lock2 = lock._get_async_lock()
        assert lock2 is not None
        assert isinstance(lock2, asyncio.Lock)

        # Should work normally
        async with lock2:
            pass

    @pytest.mark.asyncio
    async def test_concurrent_get_async_lock(self):
        """
        Test that concurrent calls to _get_async_lock from multiple threads
        always return valid locks.

        This test verifies thread safety under concurrent access.
        """
        lock = _AsyncCompatibleLock()
        results = []
        errors = []

        def get_lock_in_thread():
            """Get lock from a different thread."""
            try:
                # Need to run this in an async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(lock.__aenter__())
                    loop.run_until_complete(lock.__aexit__(None, None, None))
                    results.append(True)
                finally:
                    loop.close()
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=get_lock_in_thread)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_get_async_lock_returns_strong_reference(self):
        """
        Test that _get_async_lock always returns a strong reference.

        This verifies that the returned lock won't be garbage collected
        while still in use, addressing the core issue in #1361.
        """
        lock = _AsyncCompatibleLock()

        # Get the lock multiple times
        for _ in range(5):
            async_lock = lock._get_async_lock()

            # Verify it's a valid lock object
            assert async_lock is not None
            assert isinstance(async_lock, asyncio.Lock)

            # Verify it's actually usable (not a stale weakref)
            assert not async_lock.locked()

            # Use the lock
            async with async_lock:
                assert async_lock.locked()

            assert not async_lock.locked()

    @pytest.mark.asyncio
    async def test_get_async_lock_idempotent(self):
        """
        Test that _get_async_lock is idempotent for the same event loop.

        Multiple calls should return the same lock instance (or a valid replacement).
        """
        lock = _AsyncCompatibleLock()

        # Get multiple lock references
        locks = [lock._get_async_lock() for _ in range(10)]

        # All should be non-None
        for async_lock in locks:
            assert async_lock is not None
            assert isinstance(async_lock, asyncio.Lock)

        # All should be the same instance (since we're in the same event loop)
        # and haven't deleted any references
        first_lock = locks[0]
        for async_lock in locks[1:]:
            assert async_lock is first_lock

    @pytest.mark.asyncio
    async def test_get_async_lock_with_explicit_weakref_cleanup(self):
        """
        Test that _get_async_lock handles explicit weakref cleanup gracefully.

        This simulates the edge case where WeakValueDictionary's get() returns None
        due to timing with garbage collection.
        """
        lock = _AsyncCompatibleLock()
        current_loop = asyncio.get_running_loop()

        # Create and store a lock
        lock1 = lock._get_async_lock()
        assert lock1 is not None

        # Create a weakref to track when it's collected
        weak_lock = weakref.ref(lock1)

        # Manually manipulate the WeakValueDictionary to simulate GC
        # (In real scenario, this happens automatically)
        if current_loop in lock._async_locks:
            # Force delete to simulate GC removing the entry
            del lock._async_locks[current_loop]

        # The function should still work and create a new lock
        lock2 = lock._get_async_lock()
        assert lock2 is not None
        assert isinstance(lock2, asyncio.Lock)

        # This should be a NEW lock instance (since we deleted the old one)
        # Note: In the fixed version, we create a new lock atomically
        async with lock2:
            assert lock2.locked()


class TestWeakValueDoubleCheckFix:
    """
    Tests specifically for the double-check locking fix in _get_async_lock.

    Issue #1361: Even with double-check locking, WeakValueDictionary.get()
    could return None due to GC between the check and return.
    """

    @pytest.mark.asyncio
    async def test_double_check_handles_none_from_weakref(self):
        """
        Test that the double-check pattern handles None from WeakValueDictionary.get().

        The fix ensures that even if get() returns None (due to GC), we create
        a new lock atomically while holding the initialization lock.
        """
        lock = _AsyncCompatibleLock()
        current_loop = asyncio.get_running_loop()

        # Simulate the race condition:
        # 1. First check outside lock: lock exists, return it
        lock1 = lock._get_async_lock()
        assert lock1 is not None

        # 2. Simulate GC by removing from WeakValueDictionary
        #    (This would happen automatically in real scenario)
        del lock._async_locks[current_loop]

        # 3. Next call should handle this gracefully and create new lock
        lock2 = lock._get_async_lock()
        assert lock2 is not None
        assert isinstance(lock2, asyncio.Lock)

        # 4. Both locks should work correctly
        async with lock1:
            assert lock1.locked()

        async with lock2:
            assert lock2.locked()

    @pytest.mark.asyncio
    async def test_lock_always_created_when_missing(self):
        """
        Test that a new lock is always created if missing from WeakValueDictionary.

        This verifies the fix ensures atomic creation even if get() returns None.
        """
        lock = _AsyncCompatibleLock()
        current_loop = asyncio.get_running_loop()

        # Ensure dictionary is empty
        if current_loop in lock._async_locks:
            del lock._async_locks[current_loop]

        # Call should create a new lock atomically
        new_lock = lock._get_async_lock()
        assert new_lock is not None
        assert isinstance(new_lock, asyncio.Lock)
        assert current_loop in lock._async_locks

        # Should be usable
        async with new_lock:
            assert new_lock.locked()
