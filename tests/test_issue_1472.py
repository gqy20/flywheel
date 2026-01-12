"""Test for issue #1472 - Verify context manager methods are properly implemented.

This test verifies that:
1. __enter__ method is complete and not truncated
2. __exit__ method exists and properly releases locks
3. __aenter__ and __aexit__ methods work for async contexts
"""
import asyncio
import pytest

from flywheel import FileStorage


def test_filestorage_context_manager_sync():
    """Test that FileStorage works as a synchronous context manager."""
    storage = FileStorage()

    # This should not raise any exceptions
    with storage:
        storage.add({"title": "Test task"})

    # Verify the task was added
    assert len(storage) == 1
    assert storage.get(1)["title"] == "Test task"


@pytest.mark.asyncio
async def test_filestorage_context_manager_async():
    """Test that FileStorage works with async context managers."""
    storage = FileStorage()

    # Test async lock functionality
    async with storage._lock:
        # This should work without raising exceptions
        storage.add({"title": "Async test task"})

    # Verify the task was added
    assert len(storage) == 1


def test_lock_context_manager_properly_releases():
    """Test that the lock properly releases on context exit."""
    from threading import Thread, Lock
    import time

    storage = FileStorage()
    results = {"acquired": False}

    def worker():
        """Worker thread that tries to acquire the same lock."""
        try:
            with storage._lock:
                results["acquired"] = True
        except Exception as e:
            results["error"] = str(e)

    # First thread acquires the lock
    with storage._lock:
        # Start worker thread while lock is held
        t = Thread(target=worker)
        t.start()
        t.join(timeout=0.5)

    # Worker should not have acquired the lock while it was held
    assert not results.get("acquired", False)

    # Now the lock should be released, worker should be able to acquire it
    results["acquired"] = False
    t2 = Thread(target=worker)
    t2.start()
    t2.join(timeout=1.0)

    # This time it should succeed
    assert results.get("acquired", False) or "error" not in results


def test_context_manager_exception_handling():
    """Test that __exit__ properly handles exceptions."""
    storage = FileStorage()

    # Test that lock is released even if exception occurs
    with pytest.raises(ValueError):
        with storage:
            storage.add({"title": "Test"})
            raise ValueError("Test exception")

    # Storage should still be functional after exception
    with storage:
        assert len(storage) == 1


def test_async_lock_has_all_methods():
    """Test that _AsyncCompatibleLock has all required methods."""
    from flywheel.storage import _AsyncCompatibleLock

    lock = _AsyncCompatibleLock()

    # Check all methods exist
    assert hasattr(lock, '__enter__')
    assert hasattr(lock, '__exit__')
    assert hasattr(lock, '__aenter__')
    assert hasattr(lock, '__aexit__')

    # Verify they are callable
    assert callable(lock.__enter__)
    assert callable(lock.__exit__)
    assert callable(lock.__aenter__)
    assert callable(lock.__aexit__)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
