"""Test for issue #67 - Verify delete method is complete."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_issue_67_delete_method_complete():
    """Verify delete method works correctly and returns proper boolean values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        todo = Todo(id=1, title="Test todo")
        storage.add(todo)

        # Verify it exists
        assert storage.get(1) is not None

        # Delete the todo - should return True
        result = storage.delete(1)
        assert result is True, "delete(1) should return True when todo exists"

        # Verify it's gone
        assert storage.get(1) is None, "Todo should be deleted"

        # Try to delete again - should return False
        result = storage.delete(1)
        assert result is False, "delete(1) should return False when todo doesn't exist"

        # Test deleting non-existent todo
        result = storage.delete(999)
        assert result is False, "delete(999) should return False for non-existent todo"
