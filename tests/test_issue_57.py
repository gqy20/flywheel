"""Tests for issue #57 - Update method completeness verification."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_update_method_has_return_statement():
    """Test that update method properly returns the updated todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        original = Todo(id=1, title="Original Title", status=Status.TODO)
        storage.add(original)

        # Update the todo
        updated = Todo(id=1, title="Updated Title", status=Status.DONE)
        result = storage.update(updated)

        # Verify the update method returns the updated todo (not None)
        assert result is not None, "Update method should return the updated todo object"
        assert result.id == 1, "Returned todo should have correct ID"
        assert result.title == "Updated Title", "Returned todo should have updated title"
        assert result.status == Status.DONE, "Returned todo should have updated status"


def test_update_perserves_all_todos():
    """Test that update doesn't lose other todos in the list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add multiple todos
        storage.add(Todo(id=1, title="First", status=Status.TODO))
        storage.add(Todo(id=2, title="Second", status=Status.TODO))
        storage.add(Todo(id=3, title="Third", status=Status.TODO))

        # Update the middle todo
        updated = Todo(id=2, title="Second Updated", status=Status.DONE)
        result = storage.update(updated)

        # Verify the result is returned
        assert result is not None

        # Verify all todos are still present
        all_todos = storage.list()
        assert len(all_todos) == 3, "Update should preserve all todos"

        # Verify correct todo was updated
        assert storage.get(1).title == "First"
        assert storage.get(2).title == "Second Updated"
        assert storage.get(2).status == Status.DONE
        assert storage.get(3).title == "Third"


def test_update_saves_to_disk():
    """Test that update persists changes to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.json"

        # Create storage and add a todo
        storage = Storage(path=storage_path)
        original = Todo(id=1, title="Original", status=Status.TODO)
        storage.add(original)

        # Update the todo
        updated = Todo(id=1, title="Updated", status=Status.DONE)
        storage.update(updated)

        # Create a new Storage instance to verify persistence
        storage2 = Storage(path=storage_path)
        retrieved = storage2.get(1)

        assert retrieved.title == "Updated", "Update should persist to disk"
        assert retrieved.status == Status.DONE, "Update should persist status to disk"


def test_update_nonexistent_returns_none():
    """Test that updating non-existent todo returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Try to update a todo that doesn't exist
        nonexistent = Todo(id=999, title="Ghost", status=Status.TODO)
        result = storage.update(nonexistent)

        assert result is None, "Updating non-existent todo should return None"
