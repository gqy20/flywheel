"""Tests for file backup/rotation feature in TodoStorage.

This test suite verifies that TodoStorage.save() can create backups
of existing files before overwriting them, providing protection against
data loss from bugs or accidental deletions.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestStorageBackupDisabled:
    """Test default behavior with backups disabled."""

    def test_first_save_creates_no_backup(self, tmp_path) -> None:
        """Test that first save creates no backup when no existing file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="first todo")]
        storage.save(todos)

        # No backup file should be created
        backup = db.parent / (db.name + ".bak")
        assert not backup.exists()

    def test_second_save_creates_no_backup_by_default(self, tmp_path) -> None:
        """Test that second save does NOT create backup when backups disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        todos1 = [Todo(id=1, text="first todo")]
        storage.save(todos1)

        # Second save with different content
        todos2 = [Todo(id=1, text="modified todo")]
        storage.save(todos2)

        # No backup file should be created (default behavior)
        backup = db.parent / (db.name + ".bak")
        assert not backup.exists()


class TestStorageBackupEnabled:
    """Test backup behavior when enabled via enable_backups parameter."""

    def test_first_save_creates_no_backup(self, tmp_path) -> None:
        """Test that first save creates no backup (no existing file to backup)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        todos = [Todo(id=1, text="first todo")]
        storage.save(todos)

        # No backup file should be created (no existing file)
        backup = db.parent / (db.name + ".bak")
        assert not backup.exists()

    def test_second_save_cretes_backup_with_previous_content(self, tmp_path) -> None:
        """Test that second save creates .bak file with previous content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        # First save
        todos1 = [Todo(id=1, text="first todo"), Todo(id=2, text="second todo")]
        storage.save(todos1)

        # Second save with different content
        todos2 = [Todo(id=1, text="modified todo")]
        storage.save(todos2)

        # Backup file should exist with FIRST version
        backup = db.parent / (db.name + ".bak")
        assert backup.exists()

        # Backup should contain the original content (before overwrite)
        storage_backup = TodoStorage(str(backup))
        backed_up_todos = storage_backup.load()
        assert len(backed_up_todos) == 2
        assert backed_up_todos[0].text == "first todo"
        assert backed_up_todos[1].text == "second todo"

    def test_third_save_overwrites_backup_with_second_version(self, tmp_path) -> None:
        """Test that third save overwrites .bak with second version (rotation)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        # First save
        todos1 = [Todo(id=1, text="version 1")]
        storage.save(todos1)

        # Second save - backup will contain version 1
        todos2 = [Todo(id=1, text="version 2")]
        storage.save(todos2)

        # Verify backup contains version 1
        backup = db.parent / (db.name + ".bak")
        storage_backup = TodoStorage(str(backup))
        backed_up_todos = storage_backup.load()
        assert len(backed_up_todos) == 1
        assert backed_up_todos[0].text == "version 1"

        # Third save - backup should now contain version 2
        todos3 = [Todo(id=1, text="version 3")]
        storage.save(todos3)

        # Verify backup was overwritten with version 2
        storage_backup = TodoStorage(str(backup))
        backed_up_todos = storage_backup.load()
        assert len(backed_up_todos) == 1
        assert backed_up_todos[0].text == "version 2"

    def test_save_when_backup_creation_fails_still_succeeds(self, tmp_path) -> None:
        """Test that save succeeds even when backup creation fails."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        # First save
        todos1 = [Todo(id=1, text="original")]
        storage.save(todos1)

        # Mock shutil.copy2 to fail
        with patch("flywheel.storage.shutil.copy2") as mock_copy:
            mock_copy.side_effect = OSError("Backup creation failed")

            # This should NOT raise - save should succeed
            todos2 = [Todo(id=1, text="new version")]
            storage.save(todos2)

        # Main save should have succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "new version"

    def test_backup_preserves_metadata(self, tmp_path) -> None:
        """Test that backup preserves file metadata using shutil.copy2."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        # First save
        todos1 = [Todo(id=1, text="original")]
        storage.save(todos1)

        # Second save
        todos2 = [Todo(id=1, text="modified")]
        storage.save(todos2)

        # Backup should exist
        backup = db.parent / (db.name + ".bak")
        assert backup.exists()

        # Verify backup has the original content
        storage_backup = TodoStorage(str(backup))
        backed_up = storage_backup.load()
        assert len(backed_up) == 1
        assert backed_up[0].text == "original"

    def test_multiple_rotates_keep_only_one_backup(self, tmp_path) -> None:
        """Test that multiple saves only keep one backup file (rotation)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backups=True)

        # Perform multiple saves
        for i in range(5):
            todos = [Todo(id=1, text=f"version {i}")]
            storage.save(todos)

        # Only one backup file should exist
        backup = db.parent / (db.name + ".bak")
        assert backup.exists()

        # Backup should contain version 3 (the one before version 4)
        storage_backup = TodoStorage(str(backup))
        backed_up = storage_backup.load()
        assert len(backed_up) == 1
        assert backed_up[0].text == "version 3"
