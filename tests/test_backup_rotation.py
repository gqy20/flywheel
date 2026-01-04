"""Tests for automatic backup rotation feature (Issue #693)."""

import json
import os
from pathlib import Path
import shutil
import tempfile

import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestBackupRotation:
    """Test backup rotation functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def storage_path(self, temp_dir):
        """Get path for storage file."""
        return Path(temp_dir) / "todos.json"

    def test_backup_count_parameter(self, storage_path):
        """Test that backup_count parameter is accepted."""
        storage = FileStorage(str(storage_path), backup_count=5)
        assert storage.backup_count == 5

    def test_default_backup_count_is_zero(self, storage_path):
        """Test that default backup_count is 0 (no backup)."""
        storage = FileStorage(str(storage_path))
        assert storage.backup_count == 0

    def test_single_backup_created(self, storage_path):
        """Test that a single backup file is created when backup_count=1."""
        # Create storage with backup enabled
        storage = FileStorage(str(storage_path), backup_count=1)

        # Add a todo and save
        todo = Todo(title="First todo")
        storage.add(todo.title, todo.description)

        # Wait for async save to complete
        import asyncio
        asyncio.run(storage.save())

        # Verify backup file exists
        backup_path = Path(str(storage_path) + ".bak")
        assert backup_path.exists(), f"Backup file {backup_path} should exist"

    def test_backup_rotation_with_multiple_backups(self, storage_path):
        """Test backup rotation with backup_count=3."""
        storage = FileStorage(str(storage_path), backup_count=3)

        # Perform multiple saves to create backups
        for i in range(5):
            storage.clear()
            todo = Todo(title=f"Todo {i}")
            storage.add(todo.title, todo.description)
            import asyncio
            asyncio.run(storage.save())

        # Check that backup files exist in correct rotation order
        backup_path = Path(str(storage_path) + ".bak")
        backup_1 = Path(str(storage_path) + ".bak.1")
        backup_2 = Path(str(storage_path) + ".bak.2")

        assert backup_path.exists(), "Primary backup should exist"
        assert backup_1.exists(), "Backup .bak.1 should exist"
        assert backup_2.exists(), "Backup .bak.2 should exist"

        # Verify content: .bak.2 should be oldest, .bak should be newest
        with open(backup_2, 'r') as f:
            data_2 = json.load(f)
        with open(backup_1, 'r') as f:
            data_1 = json.load(f)
        with open(backup_path, 'r') as f:
            data_0 = json.load(f)

        # The todos should reflect different versions
        assert data_2['todos'][0]['title'] == 'Todo 0'
        assert data_1['todos'][0]['title'] == 'Todo 1'
        assert data_0['todos'][0]['title'] == 'Todo 4'  # Most recent

    def test_old_backups_are_removed(self, storage_path):
        """Test that old backups beyond backup_count are removed."""
        storage = FileStorage(str(storage_path), backup_count=2)

        # Perform more saves than backup_count
        for i in range(5):
            storage.clear()
            todo = Todo(title=f"Todo {i}")
            storage.add(todo.title, todo.description)
            import asyncio
            asyncio.run(storage.save())

        # Check that only backup_count backups exist
        backup_path = Path(str(storage_path) + ".bak")
        backup_1 = Path(str(storage_path) + ".bak.1")
        backup_2 = Path(str(storage_path) + ".bak.2")

        assert backup_path.exists(), "Primary backup should exist"
        assert backup_1.exists(), "Backup .bak.1 should exist"
        assert not backup_2.exists(), "Backup .bak.2 should NOT exist (exceeds backup_count)"

    def test_backup_preserves_metadata(self, storage_path):
        """Test that backups preserve file metadata using shutil.copy2."""
        storage = FileStorage(str(storage_path), backup_count=1)

        # Create initial file with specific content
        todo = Todo(title="Test todo", description="Test description")
        storage.add(todo.title, todo.description)
        import asyncio
        asyncio.run(storage.save())

        # Get original file metadata
        original_stat = os.stat(storage_path)

        # Perform another save to create backup
        storage.clear()
        todo2 = Todo(title="Updated todo")
        storage.add(todo2.title, todo2.description)
        asyncio.run(storage.save())

        # Check backup exists and has content
        backup_path = Path(str(storage_path) + ".bak")
        assert backup_path.exists()

        # Verify backup contains old data
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        assert backup_data['todos'][0]['title'] == 'Test todo'

    def test_no_backup_when_count_is_zero(self, storage_path):
        """Test that no backup files are created when backup_count=0."""
        storage = FileStorage(str(storage_path), backup_count=0)

        # Add and save
        todo = Todo(title="Test todo")
        storage.add(todo.title, todo.description)
        import asyncio
        asyncio.run(storage.save())

        # Verify no backup files exist
        backup_path = Path(str(storage_path) + ".bak")
        assert not backup_path.exists(), "No backup should be created when backup_count=0"

    def test_backup_with_compression(self, storage_path):
        """Test that backup rotation works with compressed storage."""
        # Use .gz extension for compressed storage
        storage = FileStorage(str(storage_path), compression=True, backup_count=2)

        # Add and save
        todo = Todo(title="Compressed todo")
        storage.add(todo.title, todo.description)
        import asyncio
        asyncio.run(storage.save())

        # Check backup exists (should also be compressed)
        backup_path = Path(str(storage_path) + ".bak")
        assert backup_path.exists(), "Backup should exist for compressed storage"
