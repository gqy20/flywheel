"""Tests for issue #60 - Update method completeness."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_update_method_returns_updated_todo():
    """Test that update method returns the updated todo object."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        original = Todo(id=1, title="Original Title", status=Status.TODO)
        storage.add(original)

        # Update the todo
        updated = Todo(id=1, title="Updated Title", status=Status.DONE)
        result = storage.update(updated)

        # Verify the update method returns the updated todo
        assert result is not None, "Update should return the updated todo"
        assert result.id == 1
        assert result.title == "Updated Title"
        assert result.status == Status.DONE

        # Verify the todo was actually updated in storage
        retrieved = storage.get(1)
        assert retrieved.title == "Updated Title"
        assert retrieved.status == Status.DONE


def test_update_method_saves_to_disk():
    """Test that update method persists changes to disk."""
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

        assert retrieved.title == "Updated"
        assert retrieved.status == Status.DONE


def test_update_nonexistent_todo_returns_none():
    """Test that updating a non-existent todo returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Try to update a todo that doesn't exist
        nonexistent = Todo(id=999, title="Ghost", status=Status.TODO)
        result = storage.update(nonexistent)

        assert result is None, "Updating non-existent todo should return None"


def test_update_modifies_in_memory_list():
    """Test that update properly modifies the in-memory todos list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add multiple todos
        storage.add(Todo(id=1, title="First", status=Status.TODO))
        storage.add(Todo(id=2, title="Second", status=Status.TODO))
        storage.add(Todo(id=3, title="Third", status=Status.TODO))

        # Update the second todo
        updated = Todo(id=2, title="Second Updated", status=Status.DONE)
        storage.update(updated)

        # Verify all todos are still present
        all_todos = storage.list()
        assert len(all_todos) == 3

        # Verify the correct todo was updated
        first = storage.get(1)
        second = storage.get(2)
        third = storage.get(3)

        assert first.title == "First"
        assert first.status == Status.TODO

        assert second.title == "Second Updated"
        assert second.status == Status.DONE

        assert third.title == "Third"
        assert third.status == Status.TODO
