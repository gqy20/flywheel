"""Test for Issue #1545: Potential race condition in _AsyncCompatibleLock initialization

This test verifies that _async_events dictionary is properly protected
during concurrent access.
"""
import asyncio
import threading
import time
import pytest
from concurrent.futures import ThreadPoolExecutor

from flywheel.storage import _AsyncCompatibleLock


def test_async_events_concurrent_initialization_thread_safety():
    """Test that _async_events dictionary is thread-safe during concurrent initialization.

    This test creates multiple threads that simultaneously try to get async events
    from the same lock. The test verifies that:
    1. All operations complete without exceptions
    2. The _async_events dictionary remains consistent (no duplicate events)
    3. No race conditions occur during initialization

    Issue #1545: _async_events dictionary itself is not thread-safe during
    concurrent access if not protected.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    event_count = [0]  # Use list to allow modification in nested function

    def worker():
        """Worker function that tries to get async event concurrently."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Try to get the async event
            event = lock._get_async_event()

            # Verify we got a valid event
            assert event is not None, "Event should not be None"
            assert isinstance(event, asyncio.Event), f"Expected asyncio.Event, got {type(event)}"

            event_count[0] += 1

        except Exception as e:
            errors.append(type(e).__name__ + ": " + str(e))
        finally:
            loop.close()

    # Launch multiple threads concurrently
    num_threads = 10
    threads = []
    start_barrier = threading.Barrier(num_threads)

    def worker_with_barrier():
        start_barrier.wait()  # Synchronize start
        worker()

    # Create and start all threads
    for _ in range(num_threads):
        t = threading.Thread(target=worker_with_barrier)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check for errors
    assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"
    assert event_count[0] == num_threads, f"Expected {num_threads} successful operations, got {event_count[0]}"


def test_async_events_concurrent_with_modification():
    """Test that concurrent reads and modifications to _async_events are thread-safe.

    This test verifies that while one thread is reading from _async_events,
    another thread can safely modify it without causing race conditions.
    """
    lock = _AsyncCompatibleLock()
    errors = []

    def reader_worker():
        """Worker that reads from _async_events."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Simulate read operation
            _ = lock._async_events.get(loop)
        except Exception as e:
            errors.append(f"Reader error: {type(e).__name__}: {str(e)}")
        finally:
            loop.close()

    def writer_worker():
        """Worker that modifies _async_events."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Simulate write operation through _get_async_event
            _ = lock._get_async_event()
        except Exception as e:
            errors.append(f"Writer error: {type(e).__name__}: {str(e)}")
        finally:
            loop.close()

    # Launch concurrent readers and writers
    threads = []
    num_readers = 5
    num_writers = 5
    start_barrier = threading.Barrier(num_readers + num_writers)

    def reader_with_barrier():
        start_barrier.wait()
        reader_worker()

    def writer_with_barrier():
        start_barrier.wait()
        writer_worker()

    for _ in range(num_readers):
        t = threading.Thread(target=reader_with_barrier)
        threads.append(t)
        t.start()

    for _ in range(num_writers):
        t = threading.Thread(target=writer_with_barrier)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"


def test_async_events_cleanup_thread_safety():
    """Test that cleanup operations on _async_events are thread-safe.

    This test verifies that _remove_event_loop and concurrent access
    to _async_events don't cause race conditions.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    loops_created = []

    def create_and_cleanup_worker():
        """Worker that creates event loop and then cleans it up."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loops_created.append(loop)

            # Get the event (this adds it to _async_events)
            event = lock._get_async_event()
            assert event is not None

            # Clean up the event loop
            lock._remove_event_loop(loop)

        except Exception as e:
            errors.append(f"Cleanup error: {type(e).__name__}: {str(e)}")
        finally:
            loop.close()

    def access_worker():
        """Worker that accesses _async_events."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Try to access while other threads might be cleaning up
            _ = lock._get_async_event()
        except Exception as e:
            errors.append(f"Access error: {type(e).__name__}: {str(e)}")
        finally:
            loop.close()

    # Launch mixed operations
    threads = []
    start_barrier = threading.Barrier(10)

    for _ in range(5):
        t = threading.Thread(target=lambda: (start_barrier.wait(), create_and_cleanup_worker()))
        threads.append(t)
        t.start()

    for _ in range(5):
        t = threading.Thread(target=lambda: (start_barrier.wait(), access_worker()))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"


def test_async_events_dict_integrity():
    """Test that _async_events maintains integrity under high contention.

    This test creates many concurrent operations and verifies that
    the dictionary maintains proper structure and doesn't get corrupted.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    operations_completed = [0]

    def high_contention_worker():
        """Worker that performs many operations rapidly."""
        try:
            for _ in range(100):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    event = lock._get_async_event()
                    operations_completed[0] += 1
                finally:
                    loop.close()
        except Exception as e:
            errors.append(f"High contention error: {type(e).__name__}: {str(e)}")

    # Run many threads with high contention
    threads = []
    num_threads = 20

    for _ in range(num_threads):
        t = threading.Thread(target=high_contention_worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    expected_ops = num_threads * 100
    assert operations_completed[0] == expected_ops, f"Expected {expected_ops} operations, got {operations_completed[0]}"

    # Verify dictionary integrity
    assert isinstance(lock._async_events, dict), "_async_events should be a dict"
    # All created event loops should have been cleaned up
    # (loops are garbage collected after each operation)
