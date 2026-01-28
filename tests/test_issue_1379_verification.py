"""Test to verify issue #1379 is a false positive.

This test confirms that __aenter__ and __aexit__ methods are fully implemented
and working correctly in the _AsyncCompatibleLock class.
"""

import asyncio
from flywheel.storage import _AsyncCompatibleLock


async def test_async_context_manager_is_complete():
    """Verify that __aenter__ and __aexit__ are fully implemented.

    This test demonstrates that both methods exist and work correctly,
    proving that issue #1379 is a false positive.
    """
    lock = _AsyncCompatibleLock()

    # Test that __aenter__ exists and can be called
    assert hasattr(lock, '__aenter__'), "__aenter__ method is missing"
    assert hasattr(lock, '__aexit__'), "__aexit__ method is missing"

    # Test that async context manager protocol works
    async with lock:
        # Successfully acquired lock via __aenter__
        assert lock._async_locked, "Lock should be acquired"

        # Do some work
        await asyncio.sleep(0.01)

    # Lock should be released via __aexit__
    assert not lock._async_locked, "Lock should be released"


async def test_async_context_manager_exception_handling():
    """Verify that __aexit__ properly handles exceptions.

    This ensures the full implementation is in place.
    """
    lock = _AsyncCompatibleLock()

    try:
        async with lock:
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Lock should still be released even after exception
    assert not lock._async_locked, "Lock should be released after exception"


if __name__ == '__main__':
    print("Running test_async_context_manager_is_complete...")
    asyncio.run(test_async_context_manager_is_complete())
    print("PASSED - __aenter__ and __aexit__ are fully implemented")

    print("\nRunning test_async_context_manager_exception_handling...")
    asyncio.run(test_async_context_manager_exception_handling())
    print("PASSED - Exception handling works correctly")

    print("\n✅ All tests passed! Issue #1379 is a false positive.")
