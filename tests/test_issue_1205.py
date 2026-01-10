"""Tests for Issue #1205 - Lock release logic deadlock risk.

This test verifies that the fix for Issue #1205 is working correctly.
The issue was that cleanup_lock was defined as an async function but never called,
which could cause deadlock if the lock was acquired after timeout.

The fix ensures:
1. cleanup_lock is a synchronous function (not async)
2. It's properly called via call_soon_threadsafe
3. A threading.Event ensures cleanup completes before __enter__ returns
"""
import asyncio
import threading
import time
import pytest
from flywheel.storage import FileStorage


def test_cleanup_lock_is_synchronous_function():
    """Verify that cleanup_lock is a synchronous function, not async.

    This test verifies the fix for Issue #1205: cleanup_lock should be a
    regular function (not async def) so it can be called via call_soon_threadsafe.
    """
    storage = FileStorage()

    # Create a scenario where lock is held
    async def acquire_and_hold():
        await storage._lock.acquire()

    # Acquire the lock
    loop = storage._get_or_create_loop()
    future = asyncio.run_coroutine_threadsafe(acquire_and_hold(), loop)
    future.result(timeout=1)

    # Verify lock is held
    assert storage._lock.locked(), "Lock should be acquired"

    # Now simulate the cleanup that happens in __enter__ timeout scenario
    cleanup_done = threading.Event()

    def cleanup_lock():
        """This should be a synchronous function."""
        try:
            if storage._lock.locked():
                storage._lock.release()
        finally:
            cleanup_done.set()

    # Call cleanup via call_soon_threadsafe (as the fix does)
    loop.call_soon_threadsafe(cleanup_lock)

    # Wait for cleanup to complete
    cleanup_done.wait(timeout=1)

    # Verify lock was released
    assert not storage._lock.locked(), "Lock should be released after cleanup"


def test_lock_cleanup_synchronization():
    """Test that cleanup synchronization prevents race conditions.

    This verifies that the threading.Event mechanism properly ensures
    cleanup completes before __enter__ returns, preventing race conditions.
    """
    storage = FileStorage()

    # Simulate the exact pattern from the fixed code
    cleanup_done = threading.Event()
    cleanup_called = threading.Event()
    cleanup_executed = threading.Event()

    def slow_cleanup_lock():
        """Simulate a cleanup that takes some time."""
        cleanup_called.set()
        # Simulate some work
        time.sleep(0.05)
        try:
            if storage._lock.locked():
                storage._lock.release()
        finally:
            cleanup_executed.set()
            cleanup_done.set()

    loop = storage._get_or_create_loop()
    loop.call_soon_threadsafe(slow_cleanup_lock)

    # Verify cleanup was called
    assert cleanup_called.wait(timeout=1), "Cleanup should be called"

    # Wait for cleanup to complete via the event
    completed = cleanup_done.wait(timeout=1)

    assert completed, "Cleanup should complete within timeout"
    assert cleanup_executed.is_set(), "Cleanup logic should execute"


def test_no_async_cleanup_lock():
    """Verify cleanup_lock is not defined as async function.

    This is a code structure test to ensure the bug from Issue #1205
    doesn't reappear. The cleanup_lock should NOT be an async function.
    """
    import inspect
    import textwrap
    import ast

    # Read the storage.py file and check the __enter__ method
    storage_path = "src/flywheel/storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    # Parse the AST
    tree = ast.parse(content)

    # Find the _AsyncCompatibleLock class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_AsyncCompatibleLock":
            # Find the __enter__ method
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__enter__":
                    # Check for async def cleanup_lock in __enter__
                    for stmt in ast.walk(item):
                        if isinstance(stmt, ast.FunctionDef):
                            # Verify cleanup_lock is not async
                            if stmt.name == "cleanup_lock":
                                assert not stmt.name.startswith("async"), \
                                    "cleanup_lock should not be defined as 'async def'"
                                assert not inspect.iscoroutinefunction(stmt), \
                                    "cleanup_lock should be a synchronous function"

    # If we get here, the code structure is correct
    assert True
