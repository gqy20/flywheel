"""Tests for file integrity verification on load (Issue #237).

Tests that corrupted JSON files trigger proper error handling with backup creation.
"""

import tempfile
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_corrupted_json_creates_backup_and_raises_error():
    """Test that corrupted JSON file creates backup and raises RuntimeError with user-friendly message."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.json"

        # First, create a valid todos file with some data
        storage = Storage(path=storage_path)
        storage.add(Todo(id=1, title="First todo"))
        storage.add(Todo(id=2, title="Second todo"))
        storage.add(Todo(id=3, title="Third todo"))

        # Verify they were saved correctly
        assert len(storage.list()) == 3

        # Now corrupt the JSON file manually (simulate partial write or corruption)
        with open(storage_path, "w") as f:
            f.write('{"todos": [{"id": 1, "title": "First todo", "status": "pending"}')  # Missing closing braces

        # Attempting to create a new Storage instance should:
        # 1. Create a backup of the corrupted file
        # 2. Raise a RuntimeError with a user-friendly message
        import os
        backup_path = f"{storage_path}.backup"

        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=storage_path)

        # Verify the error message is user-friendly
        error_message = str(exc_info.value)
        assert "Invalid JSON" in error_message or "corrupt" in error_message.lower()
        assert "Backup" in error_message or "backup" in error_message.lower()
        assert storage_path in error_message

        # Verify backup was created
        assert os.path.exists(backup_path), "Backup file should be created when JSON is corrupted"

        # Verify backup contains the corrupted data
        with open(backup_path, "r") as f:
            backup_content = f.read()
        assert '{"todos":' in backup_content


def test_truncated_json_file_handling():
    """Test that a truncated JSON file (simulating incomplete write) is handled properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.json"

        # Create a valid file first
        storage = Storage(path=storage_path)
        storage.add(Todo(id=1, title="Task 1"))
        storage.add(Todo(id=2, title="Task 2"))

        # Simulate file truncation (e.g., power failure during write)
        with open(storage_path, "r") as f:
            original_content = f.read()

        # Write only half of the content
        truncated_content = original_content[:len(original_content) // 2]
        with open(storage_path, "w") as f:
            f.write(truncated_content)

        # Should raise RuntimeError with backup
        import os
        backup_path = f"{storage_path}.backup"

        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=storage_path)

        # Verify error handling
        assert "Invalid JSON" in str(exc_info.value) or "corrupt" in str(exc_info.value).lower()
        assert os.path.exists(backup_path)


def test_invalid_json_syntax_creates_backup():
    """Test various invalid JSON syntaxes create backups and raise proper errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.json"

        # Test cases for different types of JSON corruption
        invalid_json_contents = [
            "{invalid",  # Unclosed brace
            '{"todos": [}',  # Missing array content
            '{"todos": [{"id": 1, "title": "Test"}]',  # Missing closing braces
            'not json at all',  # Completely invalid
            '{"todos": [{"id": 1, "title": "Test", "status": "pending"}], "next_id": invalid}',  # Invalid value
        ]

        import os
        backup_path = f"{storage_path}.backup"

        for invalid_content in invalid_json_contents:
            # Clean up any existing files
            if os.path.exists(storage_path):
                os.remove(storage_path)
            if os.path.exists(backup_path):
                os.remove(backup_path)

            # Write invalid JSON
            with open(storage_path, "w") as f:
                f.write(invalid_content)

            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                Storage(path=storage_path)

            # Verify backup was created
            assert os.path.exists(backup_path), f"Backup should be created for: {invalid_content[:20]}..."

            # Verify error message mentions backup
            assert "Backup" in str(exc_info.value) or "backup" in str(exc_info.value).lower()

            # Clean up for next iteration
            os.remove(backup_path)
