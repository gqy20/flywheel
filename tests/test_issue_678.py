"""Test transaction context manager for batch operations.

This test verifies issue #678 - the storage should provide a transaction()
context manager that allows users to atomically execute multiple operations.

Issue: #678
"""

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestTransactionContextManager:
    """Verify transaction() context manager for batch operations."""

    def test_transaction_method_exists(self):
        """Test that transaction() method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Verify transaction method exists
            assert hasattr(storage, 'transaction'), \
                "Storage should have a transaction() method"

    def test_transaction_returns_context_manager(self):
        """Test that transaction() returns a context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # transaction() should return something with __enter__ and __exit__
            transaction_ctx = storage.transaction()
            assert hasattr(transaction_ctx, '__enter__'), \
                "transaction() should return a context manager with __enter__"
            assert hasattr(transaction_ctx, '__exit__'), \
                "transaction() should return a context manager with __exit__"

    def test_context_manager_acquires_lock(self):
        """Test that transaction context manager acquires the lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Before entering transaction, lock should not be held
            assert storage._lock.locked() is False, \
                "Lock should not be held before transaction"

            # Enter transaction context
            with storage.transaction():
                # Lock should be held during transaction
                assert storage._lock.locked() is True, \
                    "Lock should be held during transaction"

            # After exiting transaction, lock should be released
            assert storage._lock.locked() is False, \
                "Lock should be released after transaction"

    def test_context_manager_allows_multiple_operations(self):
        """Test that transaction context manager allows multiple operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Use transaction to perform multiple operations atomically
            with storage.transaction():
                storage.add(Todo(id=None, title="Task 1"))
                storage.add(Todo(id=None, title="Task 2"))
                storage.add(Todo(id=None, title="Task 3"))

            # Verify all operations completed
            todos = storage.list()
            assert len(todos) == 3, "All three tasks should be added"
            assert todos[0].title == "Task 1"
            assert todos[1].title == "Task 2"
            assert todos[2].title == "Task 3"

    def test_context_manager_releases_lock_on_exception(self):
        """Test that transaction context manager releases lock even on exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Lock should be released even if exception occurs
            try:
                with storage.transaction():
                    assert storage._lock.locked() is True
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Lock should be released after exception
            assert storage._lock.locked() is False, \
                "Lock should be released even when exception occurs"

    def test_transaction_with_read_modify_write(self):
        """Test transaction with read-modify-write pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Add initial todos
            storage.add(Todo(id=None, title="Task 1", status="todo"))
            storage.add(Todo(id=None, title="Task 2", status="todo"))

            # Use transaction to read, modify, and write
            with storage.transaction():
                # Read
                todos = storage.list()
                assert len(todos) == 2

                # Modify - update first todo
                storage.update(1, Todo(id=1, title="Task 1 Updated", status="done"))

                # Write - add new todo
                storage.add(Todo(id=None, title="Task 3"))

            # Verify all operations completed atomically
            todos = storage.list()
            assert len(todos) == 3
            assert todos[0].title == "Task 1 Updated"
            assert todos[0].status == "done"
            assert todos[2].title == "Task 3"

    def test_transaction_is_reentrant(self):
        """Test that transaction context manager is reentrant."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # Should be able to enter transaction multiple times (reentrant)
            with storage.transaction():
                assert storage._lock.locked() is True
                storage.add(Todo(id=None, title="Task 1"))

                with storage.transaction():
                    assert storage._lock.locked() is True
                    storage.add(Todo(id=None, title="Task 2"))

                storage.add(Todo(id=None, title="Task 3"))

            # All operations should complete
            todos = storage.list()
            assert len(todos) == 3

    def test_transaction_returns_storage_instance(self):
        """Test that transaction context manager returns storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(str(storage_path))

            # transaction() should return self (the storage instance)
            with storage.transaction() as tx_storage:
                assert tx_storage is storage, \
                    "transaction() should return the storage instance"
