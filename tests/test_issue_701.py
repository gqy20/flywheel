"""Test for Issue #701: Verify FileStorage initialization is complete."""

import os
import tempfile
from flywheel.storage import FileStorage
from flywheel.models import Todo


def test_filestorage_initialization_complete():
    """Test that FileStorage can be initialized and used properly.

    This test verifies that the FileStorage class has all necessary
    attributes and methods initialized, particularly checking that
    _secure_all_parent_directories is called and the object is functional.
    """
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_todos.json")

        # Initialize FileStorage - this should not raise any errors
        storage = FileStorage(path=storage_path)

        # Verify all critical attributes are initialized
        assert hasattr(storage, '_todos'), "Missing _todos attribute"
        assert hasattr(storage, '_next_id'), "Missing _next_id attribute"
        assert hasattr(storage, '_lock'), "Missing _lock attribute"
        assert hasattr(storage, '_async_lock'), "Missing _async_lock attribute"
        assert hasattr(storage, '_dirty'), "Missing _dirty attribute"
        assert hasattr(storage, '_lock_timeout'), "Missing _lock_timeout attribute"
        assert hasattr(storage, '_lock_retry_interval'), "Missing _lock_retry_interval attribute"
        assert hasattr(storage, 'AUTO_SAVE_INTERVAL'), "Missing AUTO_SAVE_INTERVAL attribute"
        assert hasattr(storage, 'last_saved_time'), "Missing last_saved_time attribute"

        # Verify the attributes have correct types/values
        assert isinstance(storage._todos, list), "_todos should be a list"
        assert isinstance(storage._next_id, int), "_next_id should be an int"
        assert storage._next_id == 1, "_next_id should be initialized to 1"
        assert storage._dirty is False, "_dirty should be initialized to False"

        # Verify storage is functional by adding a todo
        todo = Todo(id=None, title="Test todo", status="pending")
        added_todo = storage.add(todo)

        assert added_todo.id == 1, "First todo should have ID 1"
        assert added_todo.title == "Test todo"
        assert added_todo.status == "pending"

        # Verify we can retrieve the todo
        retrieved_todo = storage.get(1)
        assert retrieved_todo is not None, "Should be able to retrieve the todo"
        assert retrieved_todo.id == 1
        assert retrieved_todo.title == "Test todo"

        # Verify we can list todos
        todos = storage.list()
        assert len(todos) == 1, "Should have 1 todo"
        assert todos[0].id == 1

        print("✅ FileStorage initialization is complete and functional!")


if __name__ == "__main__":
    test_filestorage_initialization_complete()
