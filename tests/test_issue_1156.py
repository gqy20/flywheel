"""Test for issue #1156 - _AsyncCompatibleLock.__aexit__ logic defect.

The bug is that `__aexit__` checks `locked()` before calling `release()`.
According to asyncio.Lock semantics, if we've acquired the lock in `__aenter__`,
we should always release it in `__aexit__` without checking.
"""
import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockExit:
    """Test _AsyncCompatibleLock async exit behavior."""

    @pytest.mark.asyncio
    async def test_aexit_releases_lock_properly(self):
        """Test that __aexit__ properly releases the lock."""
        lock = _AsyncCompatibleLock()

        async with lock:
            # Lock should be locked inside the context
            assert lock._async_lock.locked()

        # Lock should be released after exiting the context
        assert not lock._async_lock.locked()

    @pytest.mark.asyncio
    async def test_aexit_with_exception_still_releases(self):
        """Test that __aexit__ releases lock even when exception occurs."""
        lock = _AsyncCompatibleLock()

        with pytest.raises(ValueError):
            async with lock:
                assert lock._async_lock.locked()
                raise ValueError("test exception")

        # Lock should be released even after exception
        assert not lock._async_lock.locked()

    @pytest.mark.asyncio
    async def test_aexit_without_locked_check(self):
        """Test that release() works correctly without locked() check.

        This test verifies the fix: asyncio.Lock.release() should be called
        directly when we know we acquired the lock in __aenter__.
        The old code checked locked() first, which could cause issues.
        """
        lock = _AsyncCompatibleLock()

        # Multiple sequential uses
        for _ in range(5):
            async with lock:
                assert lock._async_lock.locked()
            # Should be released after each iteration

        assert not lock._async_lock.locked()

    @pytest.mark.asyncio
    async def test_concurrent_async_lock_usage(self):
        """Test that the lock works correctly with concurrent access."""
        lock = _AsyncCompatibleLock()
        counter = {"value": 0}
        num_tasks = 10

        async def increment():
            for _ in range(100):
                async with lock:
                    current = counter["value"]
                    await asyncio.sleep(0)  # Yield control
                    counter["value"] = current + 1

        tasks = [increment() for _ in range(num_tasks)]
        await asyncio.gather(*tasks)

        # Should be exactly num_tasks * 100 increments
        assert counter["value"] == num_tasks * 100
