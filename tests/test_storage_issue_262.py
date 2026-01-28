"""Test for Issue #262 - Verify _calculate_checksum is complete and functional."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Todo, Status


def test_calculate_checksum_complete_and_functional():
    """Test that _calculate_checksum method is complete and works correctly.

    This test verifies Issue #262 - the method should not be truncated
    and should correctly calculate SHA256 checksums of todo lists.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Create test todos
        todo1 = Todo(id=1, title="Task 1", status=Status.PENDING)
        todo2 = Todo(id=2, title="Task 2", status=Status.DONE)

        # Test _calculate_checksum method directly
        todos = [todo1, todo2]
        checksum1 = storage._calculate_checksum(todos)

        # Verify checksum is a valid hex string (SHA256 produces 64 hex characters)
        assert isinstance(checksum1, str), "Checksum should be a string"
        assert len(checksum1) == 64, f"SHA256 checksum should be 64 characters, got {len(checksum1)}"
        assert all(c in '0123456789abcdef' for c in checksum1), "Checksum should be hexadecimal"

        # Verify checksum is deterministic (same input produces same output)
        checksum2 = storage._calculate_checksum(todos)
        assert checksum1 == checksum2, "Checksum should be deterministic"

        # Verify checksum changes with different data
        todo3 = Todo(id=3, title="Task 3", status=Status.PENDING)
        todos2 = [todo1, todo3]
        checksum3 = storage._calculate_checksum(todos2)
        assert checksum1 != checksum3, "Different todos should produce different checksums"

        # Verify checksum is order-independent (due to sort_keys=True)
        todos3 = [todo2, todo1]
        checksum4 = storage._calculate_checksum(todos3)
        assert checksum1 == checksum4, "Checksum should be order-independent with sort_keys=True"


def test_calculate_checksum_empty_list():
    """Test that _calculate_checksum works with empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")
        checksum = storage._calculate_checksum([])
        assert isinstance(checksum, str), "Checksum should be a string"
        assert len(checksum) == 64, "SHA256 checksum should be 64 characters even for empty list"
