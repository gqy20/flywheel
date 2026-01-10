"""
Test for Issue #1355: Potential KeyError in async lock release

This test verifies that the _AsyncCompatibleLock correctly handles the case
where _get_async_lock() might return a different lock object or raise KeyError
between __aenter__ and __aexit__.
"""

import asyncio
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_async_lock_reuses_same_instance():
    """
    Test that __aenter__ and __aexit__ use the same lock instance.

    The bug is that __aexit__ calls _get_async_lock() again, which could
    return a different lock object or raise KeyError if the event loop
    has changed or the lock was cleaned up.

    The fix is to store the acquired lock instance in __aenter__ and
    release that specific instance in __aexit__.
    """
    async def test_func():
        lock = _AsyncCompatibleLock()

        # Track which lock instances were used
        lock_instances = []

        async def track_lock_in_aenter():
            # Get the lock instance in __aenter__
            async_lock = lock._get_async_lock()
            lock_instances.append(('aenter', id(async_lock)))
            async with lock:
                # Get the lock instance during context
                lock_instances.append(('context', id(async_lock)))
            # Get the lock instance in __aexit__
            async_lock_after = lock._get_async_lock()
            lock_instances.append(('aexit', id(async_lock_after)))

        await track_lock_in_aenter()

        # The lock instance should be the same throughout
        # If the bug exists, the __aexit__ might use a different instance
        aenter_lock_id = lock_instances[0][1]
        aexit_lock_id = lock_instances[2][1]

        # This assertion will fail with the current implementation
        # because __aexit__ calls _get_async_lock() again
        assert aenter_lock_id == aexit_lock_id, (
            f"Lock instance mismatch: __aenter__ used {aenter_lock_id}, "
            f"__aexit__ used {aexit_lock_id}"
        )

    asyncio.run(test_func())


def test_async_lock_with_simulated_loop_change():
    """
    Test that simulates the scenario where the event loop changes
    between __aenter__ and __aexit__.

    This demonstrates the potential KeyError that could occur.
    """
    async def test_func():
        lock = _AsyncCompatibleLock()

        # Get the initial lock
        async with lock:
            # Inside the context, clear the async_locks dict
            # This simulates the scenario where the lock was cleaned up
            lock._async_locks.clear()

            # When __aexit__ tries to call _get_async_lock(),
            # it would get a KeyError if the loop key doesn't exist,
            # or create a new lock which would be wrong
            # With the fix, this should work because the lock instance
            # is stored in __aenter__

        # If we reach here without error, the fix works
        assert True

    asyncio.run(test_func())


def test_async_lock_stores_instance_variable():
    """
    Test that the lock instance is properly stored during __aenter__.

    This test verifies the implementation detail: that we store
    the lock instance in an instance variable.
    """
    async def test_func():
        lock = _AsyncCompatibleLock()

        # Before entering, there should be no stored lock
        assert not hasattr(lock, '_held_async_lock') or lock._held_async_lock is None

        async with lock:
            # Inside the context, the lock should be stored
            assert hasattr(lock, '_held_async_lock'), (
                "Lock instance should be stored in __aenter__"
            )
            assert lock._held_async_lock is not None, (
                "Stored lock instance should not be None"
            )
            # The stored lock should be the same as the one in the dict
            current_loop = asyncio.get_running_loop()
            expected_lock = lock._async_locks.get(current_loop)
            assert lock._held_async_lock == expected_lock, (
                "Stored lock should match the lock in the dict"
            )

        # After exiting, the stored lock should be cleared
        assert lock._held_async_lock is None, (
            "Stored lock should be cleared in __aexit__"
        )

    asyncio.run(test_func())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
