"""
Test for issue #1356: Memory leak risk with event loop ID keys

This test verifies that using id(current_loop) as a key in WeakValueDictionary
causes memory leaks because the integer ID is still referenced by the dictionary key,
preventing automatic cleanup when the loop is garbage collected.
"""
import asyncio
import gc
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_weakvaluedictionary_with_id_key_causes_leak():
    """
    Test that demonstrates the memory leak issue with using id() as key.

    When using id(object) as a key in WeakValueDictionary, the integer key
    prevents the entry from being cleaned up even when the object is garbage collected.
    """
    # Create a WeakValueDictionary using object ID as key (current buggy behavior)
    weak_dict_with_id = weakref.WeakValueDictionary()

    # Create a temporary object and store it using its ID as key
    temp_obj = asyncio.new_event_loop()
    obj_id = id(temp_obj)
    weak_dict_with_id[obj_id] = temp_obj

    # Verify the object is in the dictionary
    assert obj_id in weak_dict_with_id
    assert len(weak_dict_with_id) == 1

    # Delete the object and force garbage collection
    del temp_obj
    gc.collect()

    # BUG: The entry still exists because the integer ID key is still referenced
    # by the dictionary itself, preventing cleanup
    assert obj_id in weak_dict_with_id, "Entry should NOT be cleaned up (bug)"
    assert len(weak_dict_with_id) == 1, "Dictionary should still have 1 entry (bug)"


def test_weakvaluedictionary_with_object_key_allows_cleanup():
    """
    Test that demonstrates the correct behavior using object as key.

    When using the object itself as a key in WeakValueDictionary, the entry
    can be properly cleaned up when the object is garbage collected.
    """
    # Create a WeakValueDictionary using object as key (correct behavior)
    weak_dict_with_obj = weakref.WeakValueDictionary()

    # Create a temporary object and store it using the object as key
    temp_obj = asyncio.new_event_loop()
    weak_dict_with_obj[temp_obj] = temp_obj

    # Verify the object is in the dictionary
    assert temp_obj in weak_dict_with_obj
    assert len(weak_dict_with_obj) == 1

    # Delete the object and force garbage collection
    obj_ref = weakref.ref(temp_obj)  # Keep a weak reference to verify deletion
    del temp_obj
    gc.collect()

    # CORRECT: The entry is cleaned up when the object is garbage collected
    assert obj_ref() is None, "Object should be garbage collected"
    assert len(weak_dict_with_obj) == 0, "Dictionary should be empty after GC"


def test_async_lock_with_loop_id_cleanup():
    """
    Test that _AsyncCompatibleLock properly cleans up locks when event loops are destroyed.

    This test will FAIL with the current implementation (using id() as key)
    and PASS after fixing the issue (using loop object as key).
    """
    # Create a new event loop
    loop = asyncio.new_event_loop()

    # Create an async lock
    lock = _AsyncCompatibleLock()

    # Get the async lock for this event loop
    # This should store the lock in _async_locks dictionary
    async_lock = lock._get_async_lock_for_loop(loop)

    # Verify the lock was created
    assert async_lock is not None
    assert len(lock._async_locks) == 1

    # Delete the event loop and force garbage collection
    loop_ref = weakref.ref(loop)
    del loop
    gc.collect()

    # BUG: With current implementation using id(loop) as key,
    # the entry is NOT cleaned up because the integer ID is still referenced
    # After fix: The entry should be cleaned up when loop is garbage collected
    assert loop_ref() is None, "Event loop should be garbage collected"

    # This assertion will FAIL with current buggy code
    # After fix, this should pass (dictionary should be empty)
    assert len(lock._async_locks) == 0, (
        "Lock dictionary should be empty after event loop is garbage collected. "
        "Current implementation causes memory leak by using id(loop) as key."
    )


def test_async_compatible_lock_get_async_lock_for_loop():
    """Helper method to get async lock for a specific loop (used in testing)."""
    # This is a monkey-patch to add testing capability
    # In actual implementation, we need to ensure the lock can be created for a given loop
    loop = asyncio.new_event_loop()

    try:
        lock = _AsyncCompatibleLock()

        # Simulate what happens in _get_async_lock but with a specific loop
        # Current implementation uses id(loop) as key
        loop_id = id(loop)

        # Manually create and store the lock (simulating the current buggy behavior)
        import threading
        async_lock = asyncio.Lock(loop=loop)
        lock._async_locks[loop_id] = async_lock

        # Verify it's stored
        assert loop_id in lock._async_locks
        assert len(lock._async_locks) == 1

        # Now test cleanup
        del loop
        gc.collect()

        # BUG: Entry still exists because of the integer ID key
        assert loop_id in lock._async_locks, "BUG: Entry not cleaned up"
        assert len(lock._async_locks) == 1, "BUG: Dictionary not empty"

    finally:
        loop.close()
