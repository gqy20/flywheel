"""Tests for backup/snapshot functionality before destructive operations.

This test suite verifies that TodoStorage can create backups before saves
and restore from those backups, providing undo capability for destructive operations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for backup file creation."""

    def test_save_creates_backup_file_when_enabled(self, tmp_path: Path) -> None:
        """Verify backup file exists after save with backup enabled when file already exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save without backup to create initial file
        initial_todos = [Todo(id=1, text="initial")]
        storage.save(initial_todos, backup_before_save=False)

        # Second save with backup enabled - should create backup
        todos = [Todo(id=1, text="updated")]
        storage.save(todos, backup_before_save=True, max_backups=3)

        # Backup file should exist (numbered as .bak.0)
        backup_path = tmp_path / "todo.json.bak.0"
        assert backup_path.exists(), "Backup file should be created"

    def test_save_without_backup_flag_creates_no_backup(self, tmp_path: Path) -> None:
        """Verify no backup is created when flag is False."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="initial")]
        storage.save(todos, backup_before_save=False)

        # No backup file should exist
        backup_path = tmp_path / ".todo.json.bak"
        assert not backup_path.exists(), "No backup file should be created"

    def test_backup_content_matches_previous_state(self, tmp_path: Path) -> None:
        """Verify backup contains the previous state, not current."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Initial save
        initial_todos = [Todo(id=1, text="initial")]
        storage.save(initial_todos, backup_before_save=False)

        # Second save with backup - backup should contain initial state
        updated_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
        storage.save(updated_todos, backup_before_save=True, max_backups=3)

        # Load backup - should have initial state
        backup_path = tmp_path / "todo.json.bak.0"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_data) == 1
        assert backup_data[0]["text"] == "initial"


class TestBackupRotation:
    """Tests for backup rotation (keeping N most recent)."""

    def test_backup_rotation_keeps_only_n_backups(self, tmp_path: Path) -> None:
        """Save 5 times with max_backups=2, verify only 2 backups retained."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 times with max_backups=2
        for i in range(5):
            todos = [Todo(id=1, text=f"save-{i}")]
            storage.save(todos, backup_before_save=True, max_backups=2)

        # Only 2 backup files should exist (numbered 0 and 1)
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 2, f"Expected 2 backups, found {len(backup_files)}"

    def test_backup_files_are_numbered_correctly(self, tmp_path: Path) -> None:
        """Verify backup files are numbered 0 (most recent) to N-1 (oldest)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save without backup to create initial file
        storage.save([Todo(id=1, text="initial")], backup_before_save=False)

        # Save 3 more times with backup - creates 3 backups
        for i in range(3):
            todos = [Todo(id=1, text=f"save-{i}")]
            storage.save(todos, backup_before_save=True, max_backups=3)

        # Check backup file names exist
        assert (tmp_path / "todo.json.bak.0").exists()
        assert (tmp_path / "todo.json.bak.1").exists()
        assert (tmp_path / "todo.json.bak.2").exists()

    def test_backup_ordering_newest_first(self, tmp_path: Path) -> None:
        """Verify bak.0 is the most recent backup, bak.1 is older, etc."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save without backup to create initial file
        storage.save([Todo(id=1, text="initial")], backup_before_save=False)

        # Save 3 more times with backup
        for i in range(3):
            todos = [Todo(id=1, text=f"save-{i}")]
            storage.save(todos, backup_before_save=True, max_backups=3)

        # bak.0 should have save-1 (most recent backup, since save-2 is in main file)
        bak_0 = json.loads((tmp_path / "todo.json.bak.0").read_text(encoding="utf-8"))
        assert bak_0[0]["text"] == "save-1"

        # bak.1 should have save-0 (older)
        bak_1 = json.loads((tmp_path / "todo.json.bak.1").read_text(encoding="utf-8"))
        assert bak_1[0]["text"] == "save-0"

        # bak.2 should have initial (oldest)
        bak_2 = json.loads((tmp_path / "todo.json.bak.2").read_text(encoding="utf-8"))
        assert bak_2[0]["text"] == "initial"


class TestBackupRestore:
    """Tests for restore_backup functionality."""

    def test_restore_from_most_recent_backup(self, tmp_path: Path) -> None:
        """Corrupt file, then restore from backup successfully."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Initial save
        initial_todos = [Todo(id=1, text="initial"), Todo(id=2, text="second")]
        storage.save(initial_todos, backup_before_save=False)

        # Save with backup
        storage.save([Todo(id=1, text="updated")], backup_before_save=True, max_backups=3)

        # Corrupt the main file
        db.write_text("corrupted data {{{", encoding="utf-8")

        # Restore from backup (n=0 = most recent)
        restored_todos = storage.load_backup(n=0)
        assert len(restored_todos) == 2
        assert restored_todos[0].text == "initial"
        assert restored_todos[1].text == "second"

    def test_restore_from_older_backup(self, tmp_path: Path) -> None:
        """Restore from backup n=1 (second most recent)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save without backup to create initial file
        storage.save([Todo(id=1, text="initial")], backup_before_save=False)

        # Save multiple times with backups
        for i in range(2):
            todos = [Todo(id=j + 1, text=f"save-{i}-todo-{j}") for j in range(i + 2)]
            storage.save(todos, backup_before_save=True, max_backups=3)

        # Restore from backup 1 (second most recent) - this has initial state
        restored = storage.load_backup(n=1)
        # Should have initial data (1 todo)
        assert len(restored) == 1
        assert restored[0].text == "initial"

    def test_restore_raises_when_no_backup_exists(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.load_backup(n=0)

    def test_restore_raises_when_backup_n_not_found(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError when requested backup index doesn't exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create one backup
        storage.save([Todo(id=1, text="test")], backup_before_save=True, max_backups=3)

        # Try to restore backup 5 (doesn't exist)
        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            storage.load_backup(n=5)


class TestBackupWithDefaultSettings:
    """Tests for default backup behavior."""

    def test_default_max_backups_is_three(self, tmp_path: Path) -> None:
        """Verify default max_backups=3 when not specified."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 times with backup enabled (default max_backups)
        for i in range(5):
            todos = [Todo(id=1, text=f"save-{i}")]
            storage.save(todos, backup_before_save=True)  # max_backups defaults to 3

        # Should have 3 backups
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) == 3
