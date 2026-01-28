"""Test for issue #695 - Verify TodoStorage initialization is complete.

This test ensures that the TodoStorage class is properly initialized
with all required attributes, specifically the _next_id attribute.
"""

import pytest
import tempfile
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.models import Todo


def test_todostorage_initialization_complete():
    """Verify TodoStorage initializes with _next_id attribute.

    This test checks that the bug where code was cut off at
    `self._next_` has been fixed and the _next_id attribute
    is properly initialized.

    Related to issue #695.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test.json"

        # Create a new TodoStorage instance
        storage = TodoStorage(storage_path)

        # Verify _next_id attribute exists and is initialized to 1
        assert hasattr(storage, "_next_id"), "TodoStorage should have _next_id attribute"
        assert storage._next_id == 1, "Initial _next_id should be 1"

        # Verify _todos attribute exists and is initialized to empty list
        assert hasattr(storage, "_todos"), "TodoStorage should have _todos attribute"
        assert storage._todos == [], "Initial _todos should be empty list"

        # Verify other critical attributes
        assert hasattr(storage, "_lock"), "TodoStorage should have _lock attribute"
        assert hasattr(storage, "_async_lock"), "TodoStorage should have _async_lock attribute"
        assert hasattr(storage, "_dirty"), "TodoStorage should have _dirty attribute"
        assert storage._dirty is False, "Initial _dirty should be False"


def test_todostorage_initialization_with_existing_file():
    """Verify TodoStorage can be initialized with existing file.

    This test ensures that even when loading from an existing file,
    the initialization completes successfully.

    Related to issue #695.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test.json"

        # Create initial storage and add a todo
        storage1 = TodoStorage(storage_path)
        todo = Todo(title="Test Todo")
        storage1.add(todo)

        # Create new storage instance with the same file
        storage2 = TodoStorage(storage_path)

        # Verify initialization completed successfully
        assert hasattr(storage2, "_next_id"), "TodoStorage should have _next_id attribute"
        assert storage2._next_id == 2, "After adding one todo, _next_id should be 2"

        # Verify the todo was loaded
        assert len(storage2._todos) == 1, "Should have loaded 1 todo from file"
        assert storage2._todos[0].title == "Test Todo", "Loaded todo should match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
