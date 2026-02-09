"""Tests for backup creation before overwriting file (Issue #2494)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Test suite for backup functionality in TodoStorage."""

    def test_save_creates_backup_before_overwrite(self, tmp_path: Any) -> None:
        """Test that save() creates a .bak file before overwriting existing data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save new data - should create backup
        new_todos = [Todo(id=1, text="new task")]
        storage.save(new_todos)

        # Verify backup was created
        backup_files = list(db.parent.glob("todo.json.bak.*"))
        assert len(backup_files) == 1, f"Expected 1 backup file, found {len(backup_files)}"

        # Verify backup contains original data
        import json

        backup_content = json.loads(backup_files[0].read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "original task"

    def test_save_creates_no_backup_when_file_doesnt_exist(self, tmp_path: Any) -> None:
        """Test that save() doesn't create backup when file doesn't exist yet."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no backup should be created
        todos = [Todo(id=1, text="first task")]
        storage.save(todos)

        # Verify no backup files were created
        backup_files = list(db.parent.glob("todo.json.bak.*"))
        assert len(backup_files) == 0

    def test_save_keeps_only_max_backups(self, tmp_path: Any) -> None:
        """Test that save() keeps only the configured max number of backups."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data (no backup since file doesn't exist)
        storage.save([Todo(id=1, text="v0")])

        # Perform multiple saves to create multiple backups
        # v1 save → backs up v0
        # v2 save → backs up v1
        # v3 save → backs up v2
        # v4 save → backs up v3
        # v5 save → backs up v4 (cleanup removes oldest: v0, v1)
        # After v5: backups are v2, v3, v4 (3 kept)
        for i in range(1, 6):
            storage.save([Todo(id=1, text=f"v{i}")])

        # Get all backup files
        backup_files = sorted(db.parent.glob("todo.json.bak.*"))

        # Verify only 3 backups are kept (default max)
        assert len(backup_files) == 3, f"Expected 3 backup files, found {len(backup_files)}"

        # Verify the backups contain the most recent versions
        # After v5 is current, we should have backups of v2, v3, v4
        # (v0 and v1 were cleaned up as they are oldest)
        import json

        backup_contents = []
        for bf in sorted(backup_files, key=lambda p: p.stat().st_mtime, reverse=True):
            content = json.loads(bf.read_text(encoding="utf-8"))
            backup_contents.append(content[0]["text"])

        # Should have 3 most recent versions before current (v5)
        assert "v4" in backup_contents
        assert "v3" in backup_contents
        assert "v2" in backup_contents

    def test_list_backups_returns_available_backups(self, tmp_path: Any) -> None:
        """Test that list_backups() returns all available backup files."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # No backups initially
        assert storage.list_backups() == []

        # Create some backups
        storage.save([Todo(id=1, text="v0")])
        storage.save([Todo(id=1, text="v1")])
        storage.save([Todo(id=1, text="v2")])

        backups = storage.list_backups()
        assert len(backups) == 2  # v0.bak and v1.bak (v2 is current)

        # Verify all are Path objects and exist
        for backup in backups:
            assert isinstance(backup, Path)
            assert backup.exists()

    def test_restore_from_backup_recovers_data(self, tmp_path: Any) -> None:
        """Test that restore_from_backup() recovers data from a backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data and save
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
        storage.save(original_todos)

        # Overwrite with new data
        storage.save([Todo(id=1, text="corrupted")])

        # Get the backup file
        backups = storage.list_backups()
        assert len(backups) == 1

        # Restore from backup
        storage.restore_from_backup(backups[0])

        # Verify original data was restored
        restored_todos = storage.load()
        assert len(restored_todos) == 2
        assert restored_todos[0].text == "original"
        assert restored_todos[1].text == "data"

    def test_restore_from_invalid_path_raises_error(self, tmp_path: Any) -> None:
        """Test that restore_from_backup() raises error for invalid path."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with pytest.raises(FileNotFoundError):
            storage.restore_from_backup("/nonexistent/backup.json.bak.123")

    def test_backup_filename_contains_timestamp(self, tmp_path: Any) -> None:
        """Test that backup filenames contain timestamps for uniqueness."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        storage.save([Todo(id=1, text="v0")])
        storage.save([Todo(id=1, text="v1")])

        backups = list(db.parent.glob("todo.json.bak.*"))

        # Backup filename should match pattern: todo.json.bak.<timestamp>
        for backup in backups:
            assert re.match(r"todo\.json\.bak\.\d+", backup.name), (
                f"Backup filename {backup.name} doesn't match expected pattern"
            )

    def test_multiple_saves_create_unique_backups(self, tmp_path: Any) -> None:
        """Test that rapid saves create unique backup files using nanosecond timestamps."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="v0")])

        # Perform multiple rapid saves
        for i in range(1, 5):
            storage.save([Todo(id=1, text=f"v{i}")])

        # Each save should create a unique backup
        backups = list(db.parent.glob("todo.json.bak.*"))
        assert len(backups) == 3, f"Expected 3 unique backups, found {len(backups)}"

    def test_cleanup_old_backups_removes_oldest(self, tmp_path: Any) -> None:
        """Test that cleanup removes oldest backups when limit is exceeded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create multiple backups
        storage.save([Todo(id=1, text="v0")])
        storage.save([Todo(id=1, text="v1")])
        storage.save([Todo(id=1, text="v2")])
        storage.save([Todo(id=1, text="v3")])
        storage.save([Todo(id=1, text="v4")])

        backups = sorted(db.parent.glob("todo.json.bak.*"))
        assert len(backups) == 3

        # Newest backups should remain
        # Oldest backup (v0 or v1) should be removed
        import json

        backup_texts = [json.loads(b.read_text(encoding="utf-8"))[0]["text"] for b in backups]
        assert "v0" not in backup_texts  # Oldest should be cleaned up
