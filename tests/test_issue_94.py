"""Tests for Issue #94 - Verify add method is complete.

Issue #94 claimed the add method was truncated at line 236.
This test verifies that the add method is fully implemented and functional.
"""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_issue_94_add_method_complete():
    """Verify that the add method is fully implemented.

    This test ensures:
    1. The add method exists and is callable
    2. It properly handles todos without IDs (auto-generates ID)
    3. It properly handles todos with explicit IDs
    4. It saves todos to storage
    5. It returns the added todo with correct ID
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Test 1: Add todo without ID - should auto-generate
        todo1 = Todo(title="Auto ID todo")
        result1 = storage.add(todo1)
        assert result1.id is not None, "Todo should have auto-generated ID"
        assert result1.id == 1, "First todo should have ID 1"
        assert result1.title == "Auto ID todo"

        # Test 2: Add another todo without ID - should increment
        todo2 = Todo(title="Second auto ID todo")
        result2 = storage.add(todo2)
        assert result2.id == 2, "Second todo should have ID 2"

        # Test 3: Add todo with explicit ID
        todo3 = Todo(id=10, title="Explicit ID todo")
        result3 = storage.add(todo3)
        assert result3.id == 10, "Todo should preserve explicit ID"

        # Test 4: Verify persistence by loading from storage
        storage2 = Storage(path=f"{tmpdir}/test.json")
        retrieved = storage2.get(1)
        assert retrieved is not None, "Todo should be persisted to storage"
        assert retrieved.title == "Auto ID todo"
        assert retrieved.id == 1

        # Test 5: Verify _next_id is properly maintained
        assert storage.get_next_id() == 11, "_next_id should be max_id + 1"


def test_issue_94_add_method_duplicate_id():
    """Verify that add method properly rejects duplicate IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo with ID 5
        todo1 = Todo(id=5, title="First")
        storage.add(todo1)

        # Try to add another todo with the same ID - should raise ValueError
        todo2 = Todo(id=5, title="Duplicate")
        try:
            storage.add(todo2)
            assert False, "Should have raised ValueError for duplicate ID"
        except ValueError as e:
            assert "already exists" in str(e)


def test_issue_94_add_method_with_status():
    """Verify that add method preserves todo status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todo with DONE status
        todo = Todo(title="Completed task", status=Status.DONE)
        result = storage.add(todo)

        assert result.status == Status.DONE, "Status should be preserved"

        # Verify persistence
        storage2 = Storage(path=f"{tmpdir}/test.json")
        retrieved = storage2.get(result.id)
        assert retrieved.status == Status.DONE
