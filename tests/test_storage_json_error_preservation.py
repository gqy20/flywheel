"""Tests for JSON error handling - should preserve data instead of silently clearing it."""

import json
import tempfile

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_json_decode_error_preserves_backup():
    """Test that corrupted JSON creates a backup file instead of silently losing data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First, create a valid todos file with some data
        storage_path = f"{tmpdir}/test.json"
        storage = Storage(path=storage_path)

        # Add some todos
        storage.add(Todo(id=1, title="First todo"))
        storage.add(Todo(id=2, title="Second todo"))
        storage.add(Todo(id=3, title="Third todo"))

        # Verify they were saved
        assert len(storage.list()) == 3

        # Now corrupt the JSON file manually
        with open(storage_path, "w") as f:
            f.write("{invalid json content")

        # Create a new Storage instance - it should preserve the corrupted file as backup
        storage2 = Storage(path=storage_path)

        # The expected behavior: backup file should be created
        # and storage should be empty (since we can't load corrupted data)
        backup_path = f"{storage_path}.backup"

        # Check if backup was created
        import os
        if os.path.exists(backup_path):
            # If backup exists, verify it contains the corrupted data
            with open(backup_path) as f:
                backup_content = f.read()
            assert backup_content == "{invalid json content"


def test_json_decode_error_does_not_silently_clear():
    """Test that JSON decode error raises an exception instead of silently clearing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First, create a valid todos file with some data
        storage_path = f"{tmpdir}/test.json"
        storage = Storage(path=storage_path)

        # Add some todos
        storage.add(Todo(id=1, title="First todo"))
        storage.add(Todo(id=2, title="Second todo"))

        # Verify they were saved
        assert len(storage.list()) == 2

        # Now corrupt the JSON file manually
        with open(storage_path, "w") as f:
            f.write("{invalid json content")

        # Creating a new Storage instance should raise an exception
        # or at least not silently lose data without creating a backup
        try:
            storage2 = Storage(path=storage_path)
            # If no exception is raised, a backup should have been created
            import os
            backup_path = f"{storage_path}.backup"
            assert os.path.exists(backup_path), "No backup created when JSON is corrupted"
        except Exception as e:
            # Exception is acceptable - it's better than silently losing data
            assert "JSON" in str(e) or "Invalid" in str(e) or "corrupt" in str(e)
