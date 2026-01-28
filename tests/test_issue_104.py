"""Tests for issue #104 - Verify add method is complete and functional."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_add_method_complete_with_duplicate_check():
    """Test that add method performs duplicate ID checking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add first todo with ID 1
        todo1 = Todo(id=1, title="First todo")
        result1 = storage.add(todo1)
        assert result1.id == 1
        assert storage.get(1) is not None

        # Try to add another todo with same ID - should raise ValueError
        todo2 = Todo(id=1, title="Duplicate ID")
        try:
            storage.add(todo2)
            assert False, "Expected ValueError for duplicate ID"
        except ValueError as e:
            assert "already exists" in str(e)


def test_add_method_with_auto_id_generation():
    """Test that add method auto-generates ID when None is provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todo without ID - should auto-generate
        todo = Todo(title="Auto-generated ID")
        result = storage.add(todo)
        assert result.id == 1
        assert storage.get(1) is not None


def test_add_method_with_external_id():
    """Test that add method handles external IDs and updates next_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todo with external high ID
        todo = Todo(id=100, title="External ID")
        result = storage.add(todo)
        assert result.id == 100
        assert storage.get_next_id() == 101  # next_id should be updated


def test_add_method_persists_to_file():
    """Test that add method persists todos to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = f"{tmpdir}/test.json"
        storage1 = Storage(path=path)

        # Add todo and close storage
        todo = Todo(id=1, title="Persistent todo")
        storage1.add(todo)

        # Create new storage instance - should load the saved todo
        storage2 = Storage(path=path)
        retrieved = storage2.get(1)
        assert retrieved is not None
        assert retrieved.title == "Persistent todo"
