"""Tests for storage transaction context manager (Issue #1453)."""

import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_transaction_context_manager_exists():
    """Test that FileStorage has a transaction method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")
        assert hasattr(storage, 'transaction'), "Storage should have a transaction() method"
        # Check it returns a context manager
        assert hasattr(storage.transaction(), '__enter__'), "transaction() should return a context manager"
        assert hasattr(storage.transaction(), '__exit__'), "transaction() should return a context manager"


def test_transaction_commits_on_success():
    """Test that changes are committed when transaction block succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add initial todo
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        # Use transaction to update status
        with storage.transaction():
            retrieved = storage.get(1)
            retrieved.status = Status.DONE
            storage.update(retrieved)

        # Verify change persisted
        final = storage.get(1)
        assert final.status == Status.DONE, "Status should be updated after successful transaction"


def test_transaction_rolls_back_on_error():
    """Test that changes are rolled back when transaction block raises an exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add initial todo with TODO status
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        initial_status = storage.get(1).status
        assert initial_status == Status.TODO

        # Use transaction but raise an error
        try:
            with storage.transaction():
                retrieved = storage.get(1)
                retrieved.status = Status.DONE
                storage.update(retrieved)
                # Simulate an error
                raise ValueError("Intentional error for testing rollback")
        except ValueError:
            pass  # Expected error

        # Verify change was rolled back - status should still be TODO
        final = storage.get(1)
        assert final.status == Status.TODO, "Status should be rolled back after failed transaction"


def test_transaction_multiple_operations():
    """Test transaction with multiple add/update operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Perform multiple operations in a transaction
        with storage.transaction():
            storage.add(Todo(id=1, title="First", status=Status.TODO))
            storage.add(Todo(id=2, title="Second", status=Status.DONE))
            storage.add(Todo(id=3, title="Third", status=Status.TODO))

        # All changes should be persisted
        assert len(storage.list()) == 3, "All todos should be added in transaction"


def test_transaction_rollback_multiple_operations():
    """Test rollback with multiple operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add one todo initially
        storage.add(Todo(id=1, title="Initial", status=Status.TODO))
        assert len(storage.list()) == 1

        # Try to add more but fail
        try:
            with storage.transaction():
                storage.add(Todo(id=2, title="Second", status=Status.DONE))
                storage.add(Todo(id=3, title="Third", status=Status.TODO))
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass

        # Should still have only the initial todo
        assert len(storage.list()) == 1, "Transaction should have rolled back all changes"
        assert storage.get(1).title == "Initial"
