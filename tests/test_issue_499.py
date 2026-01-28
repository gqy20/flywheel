"""Test for issue #499 - Verify _acquire_file_lock is complete."""

import pytest
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_acquire_file_lock_exists():
    """Test that _acquire_file_lock method exists and is callable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Verify the method exists
        assert hasattr(storage, '_acquire_file_lock')
        assert callable(storage._acquire_file_lock)

        # Verify the method signature
        import inspect
        sig = inspect.signature(storage._acquire_file_lock)
        assert 'file_handle' in sig.parameters


def test_acquire_file_lock_functional():
    """Test that _acquire_file_lock actually works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger file operations
        todo = Todo(title="Test task")
        storage.add(todo)

        # Verify the todo was saved (which means _acquire_file_lock worked)
        todos = storage.list()
        assert len(todos) == 1
        assert todos[0].title == "Test task"


def test_acquire_file_lock_and_release():
    """Test that _acquire_file_lock and _release_file_lock are paired."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Verify both methods exist
        assert hasattr(storage, '_acquire_file_lock')
        assert hasattr(storage, '_release_file_lock')
        assert callable(storage._acquire_file_lock)
        assert callable(storage._release_file_lock)

        # Perform file operations to test the lock/release cycle
        for i in range(3):
            todo = Todo(title=f"Task {i}")
            storage.add(todo)

        # Verify all todos were saved
        todos = storage.list()
        assert len(todos) == 3


def test_file_is_not_truncated():
    """Test that storage.py file is complete and not truncated."""
    import ast

    # Try to parse the storage.py file
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        source = f.read()

    # This should raise SyntaxError if the file is truncated
    try:
        ast.parse(source)
        # If we get here, the file is syntactically valid
        assert True, "storage.py is syntactically valid"
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error (possibly truncated): {e}")


def test_acquire_file_lock_has_implementation():
    """Test that _acquire_file_lock has actual implementation body."""
    import inspect

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Get the source code of _acquire_file_lock
        source = inspect.getsource(storage._acquire_file_lock)

        # Verify it's not empty or just a stub
        assert len(source) > 100, "_acquire_file_lock appears to be incomplete"
        assert 'def _acquire_file_lock' in source

        # Verify it has key implementation elements
        assert 'file_handle' in source
        assert 'os.name' in source or 'fcntl' in source
