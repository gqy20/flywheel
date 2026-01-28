"""Test storage save failure handling."""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_failure_should_raise_exception():
    """Test that _save raises exception on failure instead of silently failing."""
    # Create a storage instance
    storage = Storage()
    storage._todos = [Todo(id=1, content="Test todo", status="pending")]

    # Make the file read-only to trigger a write error
    original_path = storage.path

    # Create a temporary file and make it read-only
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = Path(f.name)
        f.write(json.dumps([]))

    try:
        # Make the file read-only
        temp_path.chmod(0o444)

        # Point storage to the read-only file
        storage.path = temp_path

        # Attempting to save should raise an exception
        with pytest.raises(Exception):
            storage._save()

    finally:
        # Clean up - restore write permissions before deleting
        temp_path.chmod(0o644)
        temp_path.unlink()
        storage.path = original_path


def test_add_should_raise_on_save_failure(mocker):
    """Test that add() raises exception when save fails."""
    storage = Storage()

    # Mock _save to raise an exception
    mocker.patch.object(storage, '_save', side_effect=PermissionError("Write failed"))

    # add() should raise the exception
    with pytest.raises(PermissionError, match="Write failed"):
        storage.add(Todo(id=1, content="Test todo", status="pending"))


def test_update_should_raise_on_save_failure(mocker):
    """Test that update() raises exception when save fails."""
    storage = Storage()
    storage._todos = [Todo(id=1, content="Test todo", status="pending")]

    # Mock _save to raise an exception
    mocker.patch.object(storage, '_save', side_effect=PermissionError("Write failed"))

    # update() should raise the exception
    with pytest.raises(PermissionError, match="Write failed"):
        storage.update(Todo(id=1, content="Updated todo", status="completed"))


def test_delete_should_raise_on_save_failure(mocker):
    """Test that delete() raises exception when save fails."""
    storage = Storage()
    storage._todos = [Todo(id=1, content="Test todo", status="pending")]

    # Mock _save to raise an exception
    mocker.patch.object(storage, '_save', side_effect=PermissionError("Write failed"))

    # delete() should raise the exception
    with pytest.raises(PermissionError, match="Write failed"):
        storage.delete(1)
