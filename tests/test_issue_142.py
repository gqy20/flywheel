"""Tests for issue #142: Verify _save_with_todos method completeness.

This test verifies that the _save_with_todos method has a complete Phase 3
implementation, which updates internal state after successful file write.
"""

import os
import tempfile

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_phase3_updates_internal_state():
    """Test that Phase 3 of _save_with_todos correctly updates internal state.

    Phase 3 should:
    1. Re-acquire the lock
    2. Update self._todos with the new todos
    3. Recalculate self._next_id if needed

    This ensures consistency between memory and disk after file write succeeds.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Verify initial state
        assert len(storage.list()) == 2
        assert storage.get_next_id() == 3

        # Update a todo (this calls _save_with_todos internally)
        todo1_updated = Todo(id=todo1.id, title="Task 1 updated", status="done")
        result = storage.update(todo1_updated)

        # Verify Phase 3 executed correctly:
        # 1. Internal state was updated
        assert result is not None
        todos = storage.list()
        assert len(todos) == 2

        # 2. self._todos reflects the change
        updated_todo = storage.get(todo1.id)
        assert updated_todo is not None
        assert updated_todo.title == "Task 1 updated"
        assert updated_todo.status == "done"

        # 3. _next_id is maintained correctly
        assert storage.get_next_id() == 3

        # 4. Disk file matches internal state
        storage2 = Storage(storage_path)
        todos_from_disk = storage2.list()
        assert len(todos_from_disk) == 2
        assert todos_from_disk[0].title == "Task 1 updated"
        assert todos_from_disk[0].status == "done"


def test_save_with_todos_phase3_with_high_id():
    """Test that Phase 3 correctly updates _next_id when new todos have higher IDs.

    This addresses Issue #101: _next_id should be recalculated when adding
    todos with externally-provided IDs that are higher than current _next_id.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add todos normally
        storage.add(Todo(title="Task 1"))
        storage.add(Todo(title="Task 2"))

        assert storage.get_next_id() == 3

        # Add a todo with a high external ID
        # This should trigger _next_id recalculation in Phase 3
        high_id_todo = Todo(id=100, title="High ID Task")
        storage.add(high_id_todo)

        # Verify Phase 3 updated _next_id correctly
        assert storage.get_next_id() == 101

        # Verify disk persistence
        storage2 = Storage(storage_path)
        assert storage2.get_next_id() == 101


def test_save_with_todos_phase3_lock_reacquisition():
    """Test that Phase 3 correctly re-acquires the lock.

    The lock should be released during I/O (Phase 2) and re-acquired
    in Phase 3 when updating internal state. This minimizes lock contention
    while ensuring thread safety.
    """
    import threading
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Flag to track when the other thread completes
        other_thread_done = threading.Event()

        def competing_operation():
            """This thread should be able to acquire the lock during Phase 2 (I/O)."""
            time.sleep(0.01)  # Give main thread time to reach Phase 2
            # Try to perform an operation - should succeed if lock is released during I/O
            storage.add(Todo(title="Competing task"))
            other_thread_done.set()

        # Start a thread that will compete for the lock
        thread = threading.Thread(target=competing_operation)
        thread.start()

        # Perform a large update (this has more I/O time, giving the other thread a chance)
        for i in range(10):
            storage.add(Todo(title=f"Task {i}"))

        thread.join(timeout=5)

        # Verify both operations completed
        assert other_thread_done.is_set(), "Other thread should have completed"
        assert len(storage.list()) >= 11  # 10 from main thread + 1 from competing thread


def test_save_with_todos_method_is_complete():
    """Verify that _save_with_todos method is syntactically complete.

    This test checks that the method has all three phases properly implemented
    and doesn't have syntax errors or incomplete blocks.
    """
    import inspect

    # Get the source code of _save_with_todos
    source = inspect.getsource(Storage._save_with_todos)

    # Check for Phase 1 (capture data under lock)
    assert "Phase 1" in source or "with self._lock" in source
    assert "todos_copy" in source

    # Check for Phase 2 (I/O operations)
    assert "json.dumps" in source
    assert "tempfile.mkstemp" in source
    assert "os.write" in source
    assert "Path(temp_path).replace" in source

    # Check for Phase 3 (update internal state after successful write)
    assert "Phase 3" in source or "self._todos = todos_copy" in source
    assert "self._next_id" in source

    # Verify the method is syntactically valid
    # If the method was truncated, this would fail
    compile(source, '<string>', 'exec')
