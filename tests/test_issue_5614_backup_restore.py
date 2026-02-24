"""Tests for backup/restore functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates backup files
before overwriting data, and provides restore_backup() to recover data.

Issue: #5614 - 添加数据备份/恢复功能
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for automatic backup creation during save()."""

    def test_save_creates_backup_file(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak file when overwriting existing data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Verify no backup yet (first save)
        backup_path = Path(str(db) + ".bak")
        assert not backup_path.exists()

        # Save again (should create backup)
        new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
        storage.save(new_todos)

        # Verify backup file was created
        assert backup_path.exists()

    def test_backup_content_matches_original(self, tmp_path: Path) -> None:
        """Test that backup file contains the original content before overwrite."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
        storage.save(original_todos)

        # Get original content
        original_content = db.read_text(encoding="utf-8")

        # Save again
        new_todos = [Todo(id=1, text="new")]
        storage.save(new_todos)

        # Verify backup contains original content
        backup_path = Path(str(db) + ".bak")
        backup_content = backup_path.read_text(encoding="utf-8")
        assert backup_content == original_content

    def test_save_without_existing_file_no_backup(self, tmp_path: Path) -> None:
        """Test that first save (no existing file) does not create backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no previous file exists
        todos = [Todo(id=1, text="first task")]
        storage.save(todos)

        # No backup should exist
        backup_path = Path(str(db) + ".bak")
        assert not backup_path.exists()

    def test_backup_file_permissions_match_original(self, tmp_path: Path) -> None:
        """Test that backup file has same permissions as original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Get original file permissions
        original_mode = db.stat().st_mode

        # Save again
        new_todos = [Todo(id=1, text="new")]
        storage.save(new_todos)

        # Verify backup has same permissions
        backup_path = Path(str(db) + ".bak")
        backup_mode = backup_path.stat().st_mode
        assert backup_mode == original_mode


class TestRestoreBackup:
    """Tests for restore_backup() method."""

    def test_restore_backup_recovers_data(self, tmp_path: Path) -> None:
        """Test that restore_backup() recovers data from backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="backup data")]
        storage.save(original_todos)

        # Save again (creates backup)
        new_todos = [Todo(id=1, text="new data")]
        storage.save(new_todos)

        # Verify current state is new data
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "new data"

        # Restore from backup
        storage.restore_backup()

        # Verify data is restored to original
        restored = storage.load()
        assert len(restored) == 2
        assert restored[0].text == "original"
        assert restored[1].text == "backup data"

    def test_restore_backup_when_no_backup_raises_error(self, tmp_path: Path) -> None:
        """Test that restore_backup() raises error when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create data (no backup yet)
        todos = [Todo(id=1, text="first")]
        storage.save(todos)

        # Try to restore when no backup exists
        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.restore_backup()

    def test_restore_backup_when_no_file_at_all(self, tmp_path: Path) -> None:
        """Test restore_backup() when neither main file nor backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # No file exists at all
        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.restore_backup()


class TestHasBackup:
    """Tests for has_backup() helper method."""

    def test_has_backup_returns_false_when_no_backup(self, tmp_path: Path) -> None:
        """Test has_backup() returns False when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no backup
        storage.save([Todo(id=1, text="first")])
        assert storage.has_backup() is False

    def test_has_backup_returns_true_after_overwrite(self, tmp_path: Path) -> None:
        """Test has_backup() returns True after save() overwrites existing data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="first")])

        # Second save creates backup
        storage.save([Todo(id=1, text="second")])
        assert storage.has_backup() is True

    def test_has_backup_returns_true_when_backup_exists(self, tmp_path: Path) -> None:
        """Test has_backup() returns True when backup file exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create backup manually
        backup_path = Path(str(db) + ".bak")
        backup_path.write_text("[]", encoding="utf-8")

        assert storage.has_backup() is True


class TestBackupOverwrite:
    """Tests for backup file behavior when overwritten multiple times."""

    def test_backup_only_keeps_most_recent(self, tmp_path: Path) -> None:
        """Test that backup only keeps the most recent previous version."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save v1
        storage.save([Todo(id=1, text="v1")])

        # Save v2 (backup = v1)
        storage.save([Todo(id=1, text="v2")])

        # Save v3 (backup = v2, v1 is gone)
        storage.save([Todo(id=1, text="v3")])

        # Restore should give v2, not v1
        storage.restore_backup()
        restored = storage.load()
        assert len(restored) == 1
        assert restored[0].text == "v2"
