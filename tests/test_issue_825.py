"""Test to verify add_batch method exists and works correctly (Issue #825).

This test verifies that the code truncation reported in issue #825
is a false positive - the add_batch method is fully implemented.
"""

import tempfile
from pathlib import Path

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_add_batch_method_exists():
    """Verify that add_batch method exists and is callable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Verify method exists
        assert hasattr(storage, 'add_batch'), "FileStorage should have add_batch method"
        assert callable(storage.add_batch), "add_batch should be callable"

        # Verify method signature
        import inspect
        sig = inspect.signature(storage.add_batch)
        params = list(sig.parameters.keys())
        assert 'todos' in params, "add_batch should have 'todos' parameter"


def test_add_batch_basic_functionality():
    """Verify that add_batch works correctly with basic input."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Test adding a batch of todos
        todos = [
            Todo(title=f"Task {i}", status="pending")
            for i in range(5)
        ]

        result = storage.add_batch(todos)

        # Verify all todos were added
        assert len(result) == 5, f"Should add 5 todos, got {len(result)}"
        assert len(storage.list()) == 5, "Storage should contain 5 todos"

        # Verify IDs were assigned
        for todo in result:
            assert todo.id is not None, "All todos should have IDs assigned"


def test_add_batch_with_empty_list():
    """Verify that add_batch handles empty list correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        result = storage.add_batch([])

        # Should return empty list
        assert result == [], "add_batch with empty list should return empty list"
        assert len(storage.list()) == 0, "Storage should remain empty"
