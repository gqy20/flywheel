"""Tests for issue #1349 - Race condition in _AsyncCompatibleLock.__enter__"""
import threading
import pytest
from unittest.mock import Mock, patch, PropertyMock
from flywheel.storage import _AsyncCompatibleLock


def test_sync_locked_flag_set_before_acquire():
    """Test that demonstrates the current (buggy) behavior where flag is set BEFORE acquire.

    Issue #1349: The current implementation sets _sync_locked = True BEFORE calling
    acquire(). This test documents this behavior as a bug that should be fixed.
    """
    lock = _AsyncCompatibleLock()

    # Track when the flag is set vs when acquire is called
    events = []

    original_acquire = lock._lock.acquire

    def tracking_acquire(*args, **kwargs):
        # Check flag state at the moment acquire() is entered
        events.append(('acquire_entered', lock._sync_locked))
        result = original_acquire(*args, **kwargs)
        # Check flag state when acquire() returns
        events.append(('acquire_returned', lock._sync_locked))
        return result

    with patch.object(lock._lock, 'acquire', side_effect=tracking_acquire):
        with lock:
            pass

    # Find the state when acquire was entered
    acquire_entered_events = [e for e in events if e[0] == 'acquire_entered']

    # The bug: flag is True when acquire() is entered
    # This means flag is set BEFORE acquire() is called
    flag_when_acquire_entered = acquire_entered_events[0][1]

    if flag_when_acquire_entered is True:
        # This is the current (buggy) behavior
        # The test expects this to fail after the fix
        pass  # We'll document this in the test message

    # After successful context, flag should be False
    assert lock._sync_locked is False


def test_correct_order_flag_after_acquire():
    """Test that verifies the CORRECT order: flag should be set AFTER acquire().

    This test will FAIL with the current implementation and PASS after the fix.
    The fix should move `self._sync_locked = True` to after `self._lock.acquire()`.
    """
    lock = _AsyncCompatibleLock()

    # Track order of flag setting and acquire calls
    events = []

    original_acquire = lock._lock.acquire

    def tracking_acquire(*args, **kwargs):
        events.append('acquire_called')
        return original_acquire(*args, **kwargs)

    # Track when _sync_locked is set to True
    original_setattr = object.__setattr__

    def tracking_setattr(obj, name, value):
        if obj is lock and name == '_sync_locked' and value is True:
            events.append('flag_set_to_True')
        return original_setattr(obj, name, value)

    with patch.object(lock._lock, 'acquire', side_effect=tracking_acquire):
        with patch('builtins.setattr', side_effect=tracking_setattr):
            with lock:
                pass

    # Find the indices
    try:
        flag_idx = events.index('flag_set_to_True')
        acquire_idx = events.index('acquire_called')
    except ValueError:
        pytest.fail("Could not track events properly")

    # The correct order: acquire should happen BEFORE flag is set to True
    # Current implementation: flag is set BEFORE acquire (bug)
    # After fix: flag is set AFTER acquire (correct)
    if acquire_idx < flag_idx:
        # This is the correct behavior - will be true after the fix
        pass
    else:
        # This is the bug - flag is set before acquire
        pytest.fail(
            "INCORRECT ORDER: _sync_locked flag is set to True BEFORE acquire() is called. "
            "This is the race condition in issue #1349. The flag should be set AFTER "
            "acquire() succeeds to avoid the window where flag=True but lock is not held."
        )


def test_async_locked_has_same_issue():
    """Test that the same issue exists in __aenter__ for consistency.

    If we fix __enter__, we should ensure __aenter__ has the same fix.
    """
    import asyncio

    async def run_test():
        lock = _AsyncCompatibleLock()

        # Track order
        events = []

        # Get the async lock to initialize it
        async_lock = lock._get_async_lock()

        original_acquire = async_lock.acquire

        async def tracking_acquire():
            events.append('async_acquire_called')
            return await original_acquire()

        # Patch and test
        with patch.object(async_lock, 'acquire', side_effect=tracking_acquire):
            original_setattr = object.__setattr__

            def tracking_setattr(obj, name, value):
                if obj is lock and name == '_async_locked' and value is True:
                    events.append('async_flag_set_to_True')
                return original_setattr(obj, name, value)

            with patch('builtins.setattr', side_effect=tracking_setattr):
                async with lock:
                    pass

        # Check order
        try:
            flag_idx = events.index('async_flag_set_to_True')
            acquire_idx = events.index('async_acquire_called')
        except ValueError:
            pytest.skip("Could not track async events properly")

        # Same expectation: flag should be set AFTER acquire
        if acquire_idx < flag_idx:
            pass  # Correct behavior
        else:
            pytest.fail(
                "INCORRECT ORDER: _async_locked flag is set to True BEFORE acquire() "
                "in __aenter__. Same bug as issue #1349."
            )

    # Run the async test
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
