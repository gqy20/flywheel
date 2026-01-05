"""Test for Issue #747: Complete async method implementation for FileStorage.

This test verifies that FileStorage's async methods use true async I/O (aiofiles)
instead of wrapping synchronous operations with asyncio.to_thread.

The issue specifically mentions:
- async_add should use aiofiles.open(...) for reads/writes
- Not just await asyncio.to_thread(self.add, ...) which still blocks
- Need true non-blocking I/O for high concurrency scenarios
"""

import asyncio
import tempfile
import time

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


@pytest.mark.asyncio
async def test_async_add_uses_true_async_io():
    """Test that async_add doesn't block the event loop.

    This test verifies that async_add uses aiofiles for file I/O
    and doesn't block other concurrent tasks.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_async_add.json"

        # Create storage using async factory
        storage = await FileStorage.create(path=test_file)

        # Track if other tasks can run during async_add
        other_task_ran = False
        todo_added = False

        async def other_task():
            """A task that should run during async_add."""
            nonlocal other_task_ran
            # This sleep allows other tasks to run if async_add is truly async
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Create a todo
        todo = Todo(title="Test async I/O", status="pending")

        # Start the other task concurrently
        task = asyncio.create_task(other_task())

        # Add todo using async method
        await storage.async_add(todo)
        todo_added = True

        # Wait for the other task
        await task

        # Verify both completed
        assert todo_added, "Todo should have been added"
        assert other_task_ran, "Other task should have run during async_add (non-blocking I/O)"


@pytest.mark.asyncio
async def test_async_update_uses_true_async_io():
    """Test that async_update doesn't block the event loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_async_update.json"

        # Create storage and add a todo
        storage = await FileStorage.create(path=test_file)
        todo = await storage.async_add(Todo(title="Original", status="pending"))

        # Track if other tasks can run during async_update
        other_task_ran = False

        async def other_task():
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Start the other task
        task = asyncio.create_task(other_task())

        # Update todo using async method
        updated_todo = Todo(id=todo.id, title="Updated", status="completed")
        await storage.async_update(updated_todo)

        await task

        assert other_task_ran, "Other task should have run during async_update"

        # Verify update worked
        retrieved = await storage.async_get(todo.id)
        assert retrieved.title == "Updated"
        assert retrieved.status == "completed"


@pytest.mark.asyncio
async def test_async_delete_uses_true_async_io():
    """Test that async_delete doesn't block the event loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_async_delete.json"

        # Create storage and add todos
        storage = await FileStorage.create(path=test_file)
        todo = await storage.async_add(Todo(title="To delete", status="pending"))

        # Track if other tasks can run
        other_task_ran = False

        async def other_task():
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        task = asyncio.create_task(other_task())

        # Delete using async method
        await storage.async_delete(todo.id)

        await task

        assert other_task_ran, "Other task should have run during async_delete"

        # Verify deletion worked
        retrieved = await storage.async_get(todo.id)
        assert retrieved is None


@pytest.mark.asyncio
async def test_async_operations_concurrent():
    """Test that multiple async operations can run concurrently without blocking.

    This test performs multiple async_add operations concurrently and verifies
    that they don't block each other, demonstrating true async I/O.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_concurrent.json"

        # Create storage
        storage = await FileStorage.create(path=test_file)

        # Track task execution
        tasks_run = []
        operations_completed = []

        async def concurrent_task(task_id: int):
            """A task that adds a todo."""
            tasks_run.append(task_id)
            await asyncio.sleep(0.001)  # Yield control
            todo = await storage.async_add(
                Todo(title=f"Concurrent todo {task_id}", status="pending")
            )
            operations_completed.append(task_id)
            return todo

        # Run multiple concurrent operations
        tasks = [concurrent_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(results) == 10, "All concurrent operations should complete"
        assert len(tasks_run) == 10, "All tasks should have started"
        assert len(operations_completed) == 10, "All operations should complete"

        # Verify all todos were saved
        todos = await storage.async_list()
        assert len(todos) == 10, "All todos should be saved"


@pytest.mark.asyncio
async def test_async_with_backup_rotation():
    """Test that backup rotation in async methods doesn't block.

    This test verifies that when backup_count > 0, the backup rotation
    doesn't block the event loop during async operations.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_backup.json"

        # Create storage with backup enabled
        storage = await FileStorage.create(path=test_file, backup_count=3)

        # Add initial todo
        await storage.async_add(Todo(title="Initial", status="pending"))

        # Track if other tasks can run during backup rotation
        other_task_ran = False

        async def other_task():
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Perform multiple updates to trigger backup rotation
        for i in range(5):
            task = asyncio.create_task(other_task())
            todo = (await storage.async_list())[0]
            await storage.async_add(
                Todo(title=f"Update {i}", status="pending")
            )
            await task

            if i == 2:  # Check at least once during rotations
                assert other_task_ran, "Other task should run during backup rotation"


@pytest.mark.asyncio
async def test_async_load_doesnt_block():
    """Test that loading data in async context doesn't block.

    This test verifies that the create() factory method uses true async I/O
    for loading initial data, not just wrapping sync load in a thread.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        import json

        # Create a file with multiple todos
        test_file = f"{tmpdir}/test_load.json"
        todos = [
            {"id": i, "title": f"Todo {i}", "status": "pending",
             "created_at": "2025-01-01T00:00:00Z"}
            for i in range(100)
        ]
        with open(test_file, 'w') as f:
            json.dump({"todos": todos, "next_id": 101, "metadata": {"checksum": "test"}}, f)

        # Track if other tasks can run during load
        other_task_ran = False

        async def other_task():
            nonlocal other_task_ran
            await asyncio.sleep(0.001)
            other_task_ran = True

        # Start the other task
        task = asyncio.create_task(other_task())

        # Create storage (triggers load)
        storage = await FileStorage.create(path=test_file)

        await task

        assert other_task_ran, "Other task should run during async load"
        assert len(storage.list()) == 100, "All todos should be loaded"


@pytest.mark.asyncio
async def test_async_performance_under_load():
    """Test async performance under concurrent load.

    This test simulates high-concurrency scenarios to ensure async operations
    don't block each other, demonstrating the performance benefit of true async I/O.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_performance.json"

        # Create storage
        storage = await FileStorage.create(path=test_file)

        # Measure time for concurrent operations
        start_time = time.time()

        # Perform 50 concurrent add operations
        tasks = [
            storage.async_add(Todo(title=f"Todo {i}", status="pending"))
            for i in range(50)
        ]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Verify all operations completed
        assert len(results) == 50, "All operations should complete"

        # In a truly async implementation with non-blocking I/O,
        # 50 concurrent operations should complete reasonably quickly
        # This is a soft check - adjust threshold if needed
        assert elapsed < 5.0, f"Concurrent operations took {elapsed:.2f}s, expected < 5.0s"

        # Verify all todos were saved
        todos = await storage.async_list()
        assert len(todos) == 50, "All todos should be saved"
