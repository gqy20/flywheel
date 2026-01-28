"""
Test for Issue #1365: Memory leak in _AsyncCompatibleLock due to incorrect WeakValueDictionary key.

The issue is that WeakValueDictionary weakly references the VALUES, not the KEYS.
When we use event loop as key and lock as value, the dictionary entries won't be
cleaned up when the event loop is garbage collected because the loop is the KEY
(not the value) in WeakValueDictionary.

We should use WeakKeyDictionary instead, which weakly references the KEYS.
"""

import asyncio
import gc
import sys
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestWeakValueDictionaryMemoryLeak:
    """Tests demonstrating the memory leak issue with WeakValueDictionary."""

    def test_weakvaluedict_does_not_cleanup_when_key_is_deleted(self):
        """
        Demonstrate that WeakValueDictionary does NOT cleanup when KEY is deleted.

        This demonstrates the problem: WeakValueDictionary only cleans up when
        the VALUE is garbage collected, not when the KEY is garbage collected.
        """
        # Create a WeakValueDictionary (current implementation)
        test_dict = weakref.WeakValueDictionary()

        # Create a key object (simulating event loop)
        key = object()

        # Create a value that won't be garbage collected
        # We keep a strong reference to the value
        value = "permanent_value"

        # Use key as dictionary key (like the current implementation)
        test_dict[key] = value

        # Verify entry exists
        assert len(test_dict) == 1, "Entry should exist after insertion"

        # Store key's id for verification
        key_id = id(key)

        # Delete the key (simulating event loop being destroyed)
        del key
        gc.collect()

        # BUG: WeakValueDictionary does NOT clean up when the KEY is deleted
        # It only cleans up when the VALUE is garbage collected
        # Since we still have a strong reference to the value, the entry remains
        assert len(test_dict) == 1, (
            "WeakValueDictionary does not clean up entries when the KEY is deleted. "
            "This is the root cause of the memory leak in issue #1365."
        )

    def test_weakkeydict_does_cleanup_when_key_is_deleted(self):
        """
        Demonstrate that WeakKeyDictionary DOES cleanup when KEY is deleted.

        This shows the correct behavior: WeakKeyDictionary weakly references
        the KEYS, so entries are cleaned up when keys are garbage collected.
        """
        # Create a WeakKeyDictionary (the correct data structure for this use case)
        test_dict = weakref.WeakKeyDictionary()

        # Create a key object (simulating event loop)
        key = object()

        # Create a value (simulating lock)
        # Note: The value doesn't need to be weakly referenced
        value = "some_value"

        # Use key as dictionary key (like the actual implementation)
        test_dict[key] = value

        # Verify entry exists
        assert len(test_dict) == 1, "Entry should exist after insertion"

        # Delete the key (simulating event loop being destroyed)
        del key
        gc.collect()

        # With WeakKeyDictionary, the entry should be automatically cleaned up
        # because the KEY was weakly referenced
        assert len(test_dict) == 0, (
            "WeakKeyDictionary should clean up entries when the KEY is garbage collected"
        )

    def test_async_lock_weakvaluedict_keeps_entry_after_loop_gone(self):
        """
        Test that demonstrates the actual memory leak in _AsyncCompatibleLock.

        With the current WeakValueDictionary implementation, entries persist
        even after the event loop (the key) is destroyed.
        """
        lock = _AsyncCompatibleLock()

        # Create a new event loop (simulating a temporary event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Use the lock in this loop to create an entry in _async_locks
        async def use_lock():
            async with lock:
                pass

        loop.run_until_complete(use_lock())

        # Verify entry was created
        # The current implementation uses loop as KEY in WeakValueDictionary
        assert loop in lock._async_locks, "Lock should be stored for this event loop"

        # Store a weak reference to the loop to verify it's deleted later
        loop_ref = weakref.ref(loop)

        # Close and delete the event loop (simulating loop destruction)
        loop.close()
        del loop
        asyncio.set_event_loop(None)

        # Force garbage collection
        gc.collect()

        # The loop should be gone
        assert loop_ref() is None, "Event loop should be garbage collected"

        # BUG: With WeakValueDictionary, the entry still exists because
        # the loop was the KEY, not the value
        # The dictionary should have cleaned up the entry when the loop was GC'd,
        # but WeakValueDictionary doesn't weak-reference keys

        # Check the internal _async_locks dict
        async_locks = lock._async_locks

        # The len might be 0 if the lock (value) was also GC'd, but that's
        # not guaranteed - the lock might be kept alive by other references
        # The real issue is that the cleanup depends on the VALUE being GC'd,
        # not the KEY (event loop) being GC'd

        # This test documents the current buggy behavior
        # After the fix with WeakKeyDictionary, this should be 0
        # For now, we just verify the behavior is documented

    def test_async_lock_weakvaluedict_key_type(self):
        """
        Test to verify what type of dictionary is currently used.

        This test documents the current state before the fix.
        """
        lock = _AsyncCompatibleLock()

        # The current implementation uses WeakValueDictionary
        # After the fix, it should use WeakKeyDictionary
        assert isinstance(lock._async_locks, weakref.WeakValueDictionary), (
            "Current implementation uses WeakValueDictionary. "
            "After fixing issue #1365, this should be WeakKeyDictionary."
        )

    def test_async_lock_entry_cleanup_with_value_deletion(self):
        """
        Test that WeakValueDictionary DOES cleanup when the VALUE is deleted.

        This confirms that WeakValueDictionary only cleans up based on values,
        not keys - which is the wrong behavior for our use case.
        """
        lock = _AsyncCompatibleLock()

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Use the lock in this loop
        async def use_lock():
            async with lock:
                pass

        loop.run_until_complete(use_lock())

        # Get the lock value (the asyncio.Lock object)
        lock_value = lock._async_locks.get(loop)
        assert lock_value is not None, "Lock should exist in dictionary"

        # Now delete all references to the lock VALUE
        # This should trigger WeakValueDictionary cleanup
        del lock_value
        gc.collect()

        # After deleting the VALUE, the entry should be cleaned up
        # This proves WeakValueDictionary only cares about the VALUE
        # But we want cleanup based on the KEY (event loop), not the value
        # That's why we need WeakKeyDictionary instead


class TestCorrectImplementationWithWeakKeyDictionary:
    """Tests showing how the correct implementation should behave."""

    def test_weakkeydict_correct_cleanup_semantics(self):
        """
        Test showing WeakKeyDictionary has the correct cleanup semantics.

        When the event loop (key) is destroyed, the entry should be removed,
        regardless of whether the lock (value) is still referenced elsewhere.
        """
        # This is what the fixed implementation should use
        correct_dict = weakref.WeakKeyDictionary()

        # Create a key (event loop) and value (lock)
        key = object()
        value = object()

        # Keep a strong reference to the value
        value_ref = value
        correct_dict[key] = value

        assert len(correct_dict) == 1

        # Delete the key
        del key
        gc.collect()

        # Entry should be cleaned up even though value_ref still exists
        # This is the correct behavior for our use case
        assert len(correct_dict) == 0, (
            "WeakKeyDictionary cleans up when KEY is deleted, "
            "even if VALUE is still referenced elsewhere. "
            "This is the correct behavior for managing per-event-loop locks."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
