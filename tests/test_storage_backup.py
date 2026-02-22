"""Tests for backup/snapshot functionality in TodoStorage.

This test suite verifies that TodoStorage can create file-based backups
before destructive operations, providing undo capability.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for backup file creation."""

    def test_save_creates_backup_file(self, tmp_path: Path) -> None:
        """Test that .bak file is created after save with backup enabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True)

        # First save creates file but no backup (nothing to backup yet)
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Second save creates backup of first version
        storage.save([Todo(id=1, text="updated")])

        # Backup files should exist (pattern: todo.json.bak.<timestamp>)
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) >= 1, "Backup file should be created"
        # Verify backup content
        backup_content = json.loads(backup_files[0].read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "initial"

    def test_save_without_backup_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that backup file is NOT created when backup is disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=False)

        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Backup file should NOT exist
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 0, "Backup file should not be created when disabled"

    def test_backup_content_matches_previous_state(self, tmp_path: Path) -> None:
        """Test that backup contains the state BEFORE the current save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True)

        # First save
        todos_v1 = [Todo(id=1, text="version 1")]
        storage.save(todos_v1)

        # Second save
        todos_v2 = [Todo(id=1, text="version 2")]
        storage.save(todos_v2)

        # Backup should contain version 1 content
        backup_files = sorted(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) >= 1, "Should have at least one backup"
        backup_content = json.loads(backup_files[0].read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "version 1"


class TestBackupRotation:
    """Tests for backup rotation with max_backups limit."""

    def test_backup_rotation_keeps_last_n_backups(self, tmp_path: Path) -> None:
        """Test that only N most recent backups are retained."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True, max_backups=2)

        # Save 5 times (creates 4 backups, then rotates to 2)
        for i in range(5):
            storage.save([Todo(id=1, text=f"version {i}")])

        # Should only have 2 backup files (pattern: todo.json.bak.*)
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 2, f"Expected 2 backups, found {len(backup_files)}"

    def test_backup_rotation_with_timestamps(self, tmp_path: Path) -> None:
        """Test that backups are timestamped for proper ordering."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True, max_backups=3)

        storage.save([Todo(id=1, text="first")])
        storage.save([Todo(id=1, text="second")])
        storage.save([Todo(id=1, text="third")])

        # Backup files should have timestamp suffixes
        backup_files = sorted(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 2  # 3 saves creates 2 backups

    def test_no_rotation_when_max_backups_is_zero(self, tmp_path: Path) -> None:
        """Test that backups accumulate without limit when max_backups=0."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True, max_backups=0)

        # Save 5 times
        for i in range(5):
            storage.save([Todo(id=1, text=f"version {i}")])

        # All 4 backups should exist (no rotation)
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 4


class TestBackupRestore:
    """Tests for restoring from backups."""

    def test_load_backup_returns_todos_from_nth_backup(self, tmp_path: Path) -> None:
        """Test that load_backup(n) returns todos from nth most recent backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True, max_backups=5)

        storage.save([Todo(id=1, text="version 0")])
        storage.save([Todo(id=1, text="version 1")])
        storage.save([Todo(id=1, text="version 2")])

        # Load most recent backup (n=0) should have version 1
        restored = storage.load_backup(n=0)
        assert len(restored) == 1
        assert restored[0].text == "version 1"

    def test_load_backup_older_backup(self, tmp_path: Path) -> None:
        """Test loading older backups (n > 0)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True, max_backups=5)

        storage.save([Todo(id=1, text="v0")])
        storage.save([Todo(id=1, text="v1")])
        storage.save([Todo(id=1, text="v2")])

        # n=1 should be second most recent backup
        restored = storage.load_backup(n=1)
        assert restored[0].text == "v0"

    def test_load_backup_raises_when_no_backups(self, tmp_path: Path) -> None:
        """Test that load_backup raises error when no backups exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=False)

        storage.save([Todo(id=1, text="test")])

        with pytest.raises(FileNotFoundError, match="No backup files found"):
            storage.load_backup(n=0)

    def test_restore_from_backup_after_corruption(self, tmp_path: Path) -> None:
        """Test that data can be restored after file corruption."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_before_save=True)

        # Save valid data twice to create a backup
        storage.save([Todo(id=1, text="important task")])
        storage.save([Todo(id=1, text="updated task")])

        # Corrupt the main file
        db.write_text("corrupted data {{{")

        # Restore from backup should work
        restored = storage.load_backup(n=0)
        assert len(restored) == 1
        assert restored[0].text == "important task"


class TestBackupIntegration:
    """Integration tests for backup with TodoApp."""

    def test_remove_creates_backup_and_can_undo(self, tmp_path: Path) -> None:
        """Test that remove operation creates backup allowing undo."""
        from flywheel.cli import TodoApp

        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db), backup_before_save=True)

        # Add todos
        app.add("task 1")
        app.add("task 2")

        # Remove one todo
        app.remove(1)

        # Current state should have only task 2
        current = app.list()
        assert len(current) == 1
        assert current[0].text == "task 2"

        # Load backup should have both tasks
        backup_todos = app.storage.load_backup(n=0)
        assert len(backup_todos) == 2
