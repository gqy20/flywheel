"""Test for issue #641: Synchronous blocking call in async context

This test verifies that FileStorage can be instantiated from an async context
without causing event loop issues due to asyncio.run() being called in __init__.
"""
import asyncio
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage


async def test_filestorage_instantiation_in_async_context():
    """Test that FileStorage can be created in async context without issues.

    This test creates FileStorage inside an async function.
    If asyncio.run() is called in __init__, it will fail because there's
    already a running event loop.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # This should work without raising RuntimeError about event loop
        storage = FileStorage(str(storage_path))

        # Verify the storage was initialized properly
        assert storage.path == storage_path
        assert storage._todos == []
        assert storage._next_id == 1


def test_filestorage_in_sync_context():
    """Test that FileStorage still works in synchronous context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # This should work in sync context too
        storage = FileStorage(str(storage_path))

        # Verify the storage was initialized properly
        assert storage.path == storage_path
        assert storage._todos == []
        assert storage._next_id == 1


async def test_filestorage_load_from_existing_file_in_async_context():
    """Test loading existing data in async context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a storage and add a todo
        storage1 = FileStorage(str(storage_path))
        storage1.add("Test todo in async context")
        storage1._cleanup()

        # Create another storage instance in async context
        # This should load the existing data
        storage2 = FileStorage(str(storage_path))

        # Verify the data was loaded
        assert len(storage2._todos) == 1
        assert storage2._todos[0].description == "Test todo in async context"


def test_nested_event_loop_detection():
    """Test that detects asyncio.run() being called in __init__.

    This test specifically catches the bug where asyncio.run() is called
    inside __init__, which fails when called from an async context.
    """
    async def create_storage():
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            return FileStorage(str(storage_path))

    # Running this should NOT raise RuntimeError about event loop already running
    result = asyncio.run(create_storage())
    assert result is not None
    assert result._todos == []
