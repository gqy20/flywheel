"""Tests for Dry Run mode (Issue #987)."""

import os
import tempfile
from pathlib import Path

from flywheel.storage import FileStorage
from flywheel.todo import Status, Todo


def test_dry_run_parameter_in_init():
    """Test that dry_run parameter is accepted in FileStorage.__init__ (Issue #987)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # This should not raise an error
        storage = FileStorage(path=f"{tmpdir}/test.json", dry_run=True)
        assert storage.dry_run is True


def test_dry_run_skip_file_writes():
    """Test that dry_run mode skips actual file writes (Issue #987)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")

        # Create storage in dry_run mode
        storage = FileStorage(path=str(test_file), dry_run=True)

        # Add a todo
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        # Verify that no file was created
        assert not test_file.exists(), "File should not exist in dry_run mode"


def test_dry_run_skip_lock_acquisition():
    """Test that dry_run mode skips lock acquisition (Issue #987)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")

        # Create storage in dry_run mode
        storage = FileStorage(path=str(test_file), dry_run=True)

        # Verify that no lock file was created
        lock_file = Path(str(test_file) + ".lock")
        assert not lock_file.exists(), "Lock file should not exist in dry_run mode"


def test_dry_run_default_false():
    """Test that dry_run defaults to False (Issue #987)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create storage without dry_run parameter
        storage = FileStorage(path=f"{tmpdir}/test.json")
        assert storage.dry_run is False


def test_dry_run_operations_in_memory():
    """Test that operations work in-memory during dry_run (Issue #987)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")

        # Create storage in dry_run mode
        storage = FileStorage(path=str(test_file), dry_run=True)

        # Add todos
        storage.add(Todo(id=1, title="First", status=Status.TODO))
        storage.add(Todo(id=2, title="Second", status=Status.DONE))

        # Operations should work in-memory
        todo = storage.get(1)
        assert todo is not None
        assert todo.title == "First"

        todos = storage.list()
        assert len(todos) == 2

        # Update should work in-memory
        todo.title = "Updated"
        storage.update(todo)
        updated = storage.get(1)
        assert updated.title == "Updated"

        # Delete should work in-memory
        result = storage.delete(1)
        assert result is True
        assert storage.get(1) is None
        assert len(storage.list()) == 1
