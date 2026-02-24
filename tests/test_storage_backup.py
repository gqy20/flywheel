"""Tests for backup/restore functionality in TodoStorage.

This test suite verifies that TodoStorage can backup data before overwriting
and restore from backup when needed.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for backup file creation."""

    def test_save_creates_backup_file(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak file before overwriting."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save again - this should create a backup of the original
        new_todos = [Todo(id=1, text="new task")]
        storage.save(new_todos)

        # Verify backup file was created
        backup_path = db.with_suffix(".json.bak")
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup content matches original (not new)
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_data) == 1
        assert backup_data[0]["text"] == "original task"

    def test_save_updates_backup_on_subsequent_save(self, tmp_path: Path) -> None:
        """Test that subsequent saves update the backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="first")])
        backup_path = db.with_suffix(".json.bak")

        # Second save
        storage.save([Todo(id=1, text="second")])

        # Backup should now contain "first"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "first"

        # Third save
        storage.save([Todo(id=1, text="third")])

        # Backup should now contain "second"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "second"

    def test_backup_not_created_when_no_original_file(self, tmp_path: Path) -> None:
        """Test that no backup is created when saving to a new file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save to a new file (no existing data)
        storage.save([Todo(id=1, text="new file")])

        backup_path = db.with_suffix(".json.bak")
        # Backup should NOT exist since there was no original file
        assert not backup_path.exists()


class TestBackupRestore:
    """Tests for restore_backup functionality."""

    def test_restore_backup_restores_data(self, tmp_path: Path) -> None:
        """Test that restore_backup() restores data from backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save original data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="tasks")]
        storage.save(original_todos)

        # Save new data (creates backup)
        storage.save([Todo(id=1, text="new data")])

        # Restore from backup
        result = storage.restore_backup()

        assert result is True, "restore_backup should return True on success"

        # Verify data was restored
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "original"
        assert loaded[1].text == "tasks"

    def test_restore_backup_returns_false_when_no_backup(self, tmp_path: Path) -> None:
        """Test that restore_backup() returns False when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create file without backup (first save to new file)
        storage.save([Todo(id=1, text="first")])
        backup_path = db.with_suffix(".json.bak")

        # Delete backup if it exists
        if backup_path.exists():
            backup_path.unlink()

        result = storage.restore_backup()
        assert result is False, "restore_backup should return False when no backup"

    def test_restore_backup_returns_false_when_no_main_file(self, tmp_path: Path) -> None:
        """Test that restore_backup() returns False when main file doesn't exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # No files exist
        result = storage.restore_backup()
        assert result is False


class TestBackupPermissions:
    """Tests for backup file permissions."""

    def test_backup_file_has_same_permissions_as_original(self, tmp_path: Path) -> None:
        """Test that backup file permissions match original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save data twice to create backup
        storage.save([Todo(id=1, text="first")])
        storage.save([Todo(id=1, text="second")])

        # Get original file permissions
        original_mode = db.stat().st_mode

        # Backup should have same permissions
        backup_path = db.with_suffix(".json.bak")
        backup_mode = backup_path.stat().st_mode

        # Compare permission bits (lower 9 bits)
        assert (original_mode & 0o777) == (backup_mode & 0o777), (
            f"Backup permissions {oct(backup_mode & 0o777)} should match "
            f"original {oct(original_mode & 0o777)}"
        )


class TestBackupPathProperty:
    """Tests for backup_path property."""

    def test_backup_path_is_sibling_of_main_file(self, tmp_path: Path) -> None:
        """Test that backup path is in same directory with .bak suffix."""
        db = tmp_path / "subdir" / "todo.json"
        storage = TodoStorage(str(db))

        backup_path = storage.backup_path

        assert backup_path.parent == db.parent
        assert backup_path.name == "todo.json.bak"

    def test_backup_path_works_with_custom_filenames(self, tmp_path: Path) -> None:
        """Test backup_path with custom database filename."""
        db = tmp_path / "mydata.json"
        storage = TodoStorage(str(db))

        backup_path = storage.backup_path

        assert backup_path.name == "mydata.json.bak"
