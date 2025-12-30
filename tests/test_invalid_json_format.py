"""Test for Issue #116: Invalid JSON format should trigger backup mechanism."""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_invalid_json_format_creates_backup():
    """Test that when JSON file has invalid format (neither dict nor list), a backup is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        backup_path = Path(str(storage_path) + ".backup")

        # Create a storage with some todos first
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="Task 1"))
        storage1.add(Todo(title="Task 2"))
        assert len(storage1.list()) == 2
        del storage1

        # Corrupt the file by writing invalid JSON format (a string instead of dict/list)
        storage_path.write_text('"just a string"')

        # Try to load the corrupted file
        # This should raise RuntimeError and create a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(str(storage_path))

        # Verify the error message mentions backup
        assert "Backup saved to" in str(exc_info.value)

        # Verify backup was created
        assert backup_path.exists()

        # Verify backup contains the corrupted data
        backup_content = backup_path.read_text()
        assert backup_content == '"just a string"'


def test_invalid_json_format_with_number():
    """Test that when JSON file contains a number, a backup is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        backup_path = Path(str(storage_path) + ".backup")

        # Create a storage with some todos first
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="Task 1"))
        storage1.add(Todo(title="Task 2"))
        assert len(storage1.list()) == 2
        del storage1

        # Corrupt the file by writing a number
        storage_path.write_text('42')

        # Try to load the corrupted file
        # This should raise RuntimeError and create a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(str(storage_path))

        # Verify the error message mentions backup
        assert "Backup saved to" in str(exc_info.value)

        # Verify backup was created
        assert backup_path.exists()

        # Verify backup contains the corrupted data
        backup_content = backup_path.read_text()
        assert backup_content == '42'


def test_invalid_json_format_with_boolean():
    """Test that when JSON file contains a boolean, a backup is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        backup_path = Path(str(storage_path) + ".backup")

        # Create a storage with some todos first
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="Task 1"))
        storage1.add(Todo(title="Task 2"))
        assert len(storage1.list()) == 2
        del storage1

        # Corrupt the file by writing a boolean
        storage_path.write_text('true')

        # Try to load the corrupted file
        # This should raise RuntimeError and create a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(str(storage_path))

        # Verify the error message mentions backup
        assert "Backup saved to" in str(exc_info.value)

        # Verify backup was created
        assert backup_path.exists()

        # Verify backup contains the corrupted data
        backup_content = backup_path.read_text()
        assert backup_content == 'true'


def test_invalid_json_format_with_null():
    """Test that when JSON file contains null, a backup is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        backup_path = Path(str(storage_path) + ".backup")

        # Create a storage with some todos first
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="Task 1"))
        storage1.add(Todo(title="Task 2"))
        assert len(storage1.list()) == 2
        del storage1

        # Corrupt the file by writing null
        storage_path.write_text('null')

        # Try to load the corrupted file
        # This should raise RuntimeError and create a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(str(storage_path))

        # Verify the error message mentions backup
        assert "Backup saved to" in str(exc_info.value)

        # Verify backup was created
        assert backup_path.exists()

        # Verify backup contains the corrupted data
        backup_content = backup_path.read_text()
        assert backup_content == 'null'
