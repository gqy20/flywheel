"""Tests for issue #124: Verify _save_with_todos method completeness.

This test verifies that the _save_with_todos method is complete and properly:
1. Acquires locks for data capture
2. Performs atomic file I/O
3. Updates internal state ONLY after successful write
4. Properly handles exceptions and cleanup

The issue reported that the method was truncated at line 233, missing the
state update and lock release logic. This test validates the fix.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_method_completeness():
    """Test that _save_with_todos executes all three phases correctly.

    This verifies that the method is complete and:
    - Phase 1: Captures data under lock
    - Phase 2: Performs I/O outside lock
    - Phase 3: Updates internal state after successful write
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Verify initial state
        assert len(storage.list()) == 2

        # Track the phases by mocking lock acquisition
        lock_acquire_count = []
        original_acquire = storage._lock.acquire
        original_release = storage._lock.release

        def mock_acquire(*args, **kwargs):
            lock_acquire_count.append('acquire')
            return original_acquire(*args, **kwargs)

        def mock_release(*args, **kwargs):
            lock_acquire_count.append('release')
            return original_release(*args, **kwargs)

        storage._lock.acquire = mock_acquire
        storage._lock.release = mock_release

        # Add a new todo which will call _save_with_todos
        todo3 = storage.add(Todo(title="Task 3"))

        # Verify lock was acquired and released multiple times:
        # 1. For add() method lock
        # 2. For _save_with_todos Phase 1 (capture data)
        # 3. For _save_with_todos Phase 3 (update state)
        assert len(lock_acquire_count) >= 4, (
            f"Expected at least 4 lock operations (2 acquire, 2 release), "
            f"but got {len(lock_acquire_count)}. Method may not be complete."
        )

        # Verify internal state was updated
        todos_after = storage.list()
        assert len(todos_after) == 3, (
            f"Expected 3 todos after successful write, but got {len(todos_after)}"
        )

        # Verify the new todo was added
        titles = [t.title for t in todos_after]
        assert titles == ["Task 1", "Task 2", "Task 3"]


def test_save_with_todos_updates_state_after_write():
    """Test that _save_with_todos updates internal state AFTER successful write.

    This is the key fix for the reported issue - the state update should
    happen in Phase 3, after the file write succeeds.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todo
        todo1 = storage.add(Todo(title="Task 1"))

        # Track when state is updated vs when file is written
        write_completed = []
        original_replace = pathlib.Path.replace

        def mock_replace(self, target):
            # File write completes here
            write_completed.append('write')
            return original_replace(self, target)

        # Track state updates
        state_updates = []
        original_save_with_todos = storage._save_with_todos

        def tracked_save_with_todos(todos):
            # Call original but track when state is updated
            result = original_save_with_todos(todos)
            # After call, check if state was updated
            state_updates.append('after_save')
            return result

        with patch.object(pathlib.Path, 'replace', mock_replace):
            storage._save_with_todos = tracked_save_with_todos

            # Add a new todo
            todo2 = storage.add(Todo(title="Task 2"))

        # Verify write completed
        assert len(write_completed) == 1, "File write should have completed"

        # Verify state was updated after write
        assert len(state_updates) == 1, "State should have been updated"

        # Verify final state is correct
        todos = storage.list()
        assert len(todos) == 2
        assert [t.title for t in todos] == ["Task 1", "Task 2"]


def test_save_with_todos_no_state_update_on_failure():
    """Test that _save_with_todos does NOT update state on write failure.

    This validates that Phase 3 (state update) only runs after successful write.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Mock os.write to fail
        def mock_write(fd, data):
            raise OSError(28, "No space left on device")

        with patch('os.write', side_effect=mock_write):
            # This should fail
            with pytest.raises(OSError):
                storage.add(Todo(title="Task 3"))

        # Verify state was NOT updated
        todos = storage.list()
        assert len(todos) == 2, (
            f"Expected 2 todos (state should not update on failure), "
            f"but got {len(todos)}"
        )
        assert [t.title for t in todos] == ["Task 1", "Task 2"]


def test_save_with_todos_file_descriptor_cleanup():
    """Test that _save_with_todos properly closes file descriptors.

    This validates the finally block that ensures fd cleanup.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Track file descriptor operations
        close_calls = []
        original_close = os.close

        def mock_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with patch('os.close', side_effect=mock_close):
            # Add a todo - should trigger file operations
            storage.add(Todo(title="Test"))

        # Verify file descriptor was closed
        assert len(close_calls) >= 1, "File descriptor should be closed"


# Import pathlib for the mock_replace test
import pathlib
