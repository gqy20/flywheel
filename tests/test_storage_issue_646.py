"""Test for Issue #646: Synchronous file I/O in _load_sync blocks the event loop.

This test verifies that FileStorage initialization should be made async-safe
to avoid blocking the event loop during file I/O operations.

The current implementation calls _load_sync() directly in __init__, which blocks
the event loop. The fix should provide an async factory method that uses
asyncio.to_thread() to run the synchronous load in a thread pool executor.
"""

import asyncio
import tempfile

import pytest

from flywheel.storage import FileStorage


@pytest.mark.asyncio
async def test_filestorage_async_factory_method():
    """Test that FileStorage provides an async factory method.

    This test checks for the existence of an async factory method that creates
    FileStorage instances without blocking the event loop. The method should be
    named `create()` or similar and use asyncio.to_thread() to run the synchronous
    file I/O in a thread pool executor.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import json
        test_file = f"{tmpdir}/test.json"

        # Create a file with some data
        with open(test_file, 'w') as f:
            json.dump([], f)

        # Check if async factory method exists
        assert hasattr(FileStorage, 'create'), (
            "FileStorage should provide an async 'create' factory method "
            "to avoid blocking the event loop during initialization"
        )

        # Create storage using async factory
        storage = await FileStorage.create(path=test_file)

        # The storage should be functional
        assert storage.list() == []


@pytest.mark.asyncio
async def test_filestorage_async_factory_does_not_block():
    """Test that FileStorage async factory doesn't block the event loop.

    This test creates a FileStorage instance using the async factory method and
    verifies that other async tasks can run concurrently during initialization.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import json
        test_file = f"{tmpdir}/test.json"

        # Create a file with some data
        with open(test_file, 'w') as f:
            json.dump([], f)

        # Track if other tasks can run
        other_task_ran = False
        storage_created = False

        async def other_task():
            """A task that should run during FileStorage creation."""
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Start the other task
        task = asyncio.create_task(other_task())

        # Create FileStorage using async factory
        storage = await FileStorage.create(path=test_file)
        storage_created = True

        # Wait for the other task
        await task

        # Verify both completed
        assert storage_created, "FileStorage should have been created"
        assert other_task_ran, "Other task should have run during creation"
        assert storage.list() == []


@pytest.mark.asyncio
async def test_multiple_filestorage_async_factory_concurrent():
    """Test that multiple FileStorage instances can be created concurrently.

    This test creates multiple FileStorage instances in parallel using the async
    factory method to ensure that the synchronous file I/O doesn't block the event loop.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import json

        # Create test files
        test_files = [f"{tmpdir}/test{i}.json" for i in range(5)]
        for test_file in test_files:
            with open(test_file, 'w') as f:
                json.dump([], f)

        # Create all storages concurrently
        tasks = [FileStorage.create(path=test_file) for test_file in test_files]
        storages = await asyncio.gather(*tasks)

        # All should have been created
        assert len(storages) == 5, "All FileStorage instances should be created"

        # All should be functional
        for storage in storages:
            assert storage.list() == []


@pytest.mark.asyncio
async def test_filestorage_async_factory_with_large_file():
    """Test FileStorage async factory with a large file.

    This test ensures that even with a larger file, the event loop is not blocked.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import json
        test_file = f"{tmpdir}/test_large.json"

        # Create a file with many todos
        todos = [
            {
                "id": i,
                "title": f"Todo {i}",
                "status": "pending",
                "created_at": "2025-01-01T00:00:00Z",
            }
            for i in range(1000)
        ]
        with open(test_file, 'w') as f:
            json.dump(todos, f)

        # Track if other tasks can run
        other_task_ran = False

        async def other_task():
            """A task that should run during FileStorage creation."""
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Start the other task
        task = asyncio.create_task(other_task())

        # Create FileStorage using async factory
        storage = await FileStorage.create(path=test_file)

        # Wait for the other task
        await task

        # Verify storage loaded correctly
        assert len(storage.list()) == 1000, "All todos should be loaded"
        assert other_task_ran, "Other task should have run during creation"
