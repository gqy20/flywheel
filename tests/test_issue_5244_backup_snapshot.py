"""Tests for backup/snapshot feature before destructive operations.

This test suite verifies that TodoStorage creates backups before save operations,
providing recovery capability when users accidentally delete todos or corrupt data.

Issue: #5244
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for backup file creation."""

    def test_save_creates_backup_file_when_enabled(self, tmp_path: Path) -> None:
        """When backup_before_save=True, backup file is created after save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save creates the file (no backup since file doesn't exist yet)
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos, backup_before_save=True)

        # Second save should create a backup (since file exists)
        todos2 = [Todo(id=1, text="test todo v2")]
        storage.save(todos2, backup_before_save=True)

        # Verify backup file exists (using .json.bak.<n> format)
        backup_files = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backup_files) >= 1, f"Backup file should exist, found: {list(tmp_path.iterdir())}"

    def test_save_without_backup_does_not_create_backup(self, tmp_path: Path) -> None:
        """When backup_before_save=False (default), no backup file is created."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos, backup_before_save=False)

        # Verify no backup file exists
        backup_path = db.with_suffix(db.suffix + ".bak")
        assert not backup_path.exists(), f"Backup file {backup_path} should not exist"

    def test_backup_contains_previous_content(self, tmp_path: Path) -> None:
        """Backup file should contain the previous version of todos."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        original_todos = [Todo(id=1, text="original todo")]
        storage.save(original_todos, backup_before_save=True)

        # Second save with different content
        new_todos = [Todo(id=1, text="modified todo"), Todo(id=2, text="new todo")]
        storage.save(new_todos, backup_before_save=True)

        # Load backup and verify it contains the original content
        backup_todos = storage.load_backup()
        assert len(backup_todos) == 1
        assert backup_todos[0].text == "original todo"


class TestBackupRotation:
    """Tests for backup rotation to keep N most recent backups."""

    def test_backup_rotation_keeps_max_backups(self, tmp_path: Path) -> None:
        """Save 5 times with max_backups=2, verify only 2 backups retained."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 times with max_backups=2
        for i in range(5):
            todos = [Todo(id=1, text=f"todo version {i}")]
            storage.save(todos, backup_before_save=True, max_backups=2)

        # Count backup files (should be exactly 2)
        backup_files = list(tmp_path.glob("todo.json.bak*"))
        assert len(backup_files) == 2, f"Expected 2 backup files, found {len(backup_files)}: {backup_files}"

    def test_backup_rotation_keeps_most_recent(self, tmp_path: Path) -> None:
        """Backup rotation should keep the most recent backups."""
        import time

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 times with max_backups=3
        # Save 0: No backup (file doesn't exist), current = "version 0"
        # Save 1: Backup of "version 0", current = "version 1"
        # Save 2: Backup of "version 1", current = "version 2"
        # Save 3: Backup of "version 2", current = "version 3"  (rotation starts, oldest deleted)
        # Save 4: Backup of "version 3", current = "version 4"  (oldest deleted)
        for i in range(5):
            todos = [Todo(id=1, text=f"version {i}")]
            storage.save(todos, backup_before_save=True, max_backups=3)
            time.sleep(0.01)  # Small delay to ensure different mtimes

        # Load backups from different positions
        # After rotation with max_backups=3, we have backups: v3 (newest), v2, v1 (oldest)
        # Most recent backup (n=0) should be version 3 (before version 4 was saved)
        backup_0 = storage.load_backup(n=0)
        assert backup_0[0].text == "version 3"

        # Second most recent backup (n=1) should be version 2
        backup_1 = storage.load_backup(n=1)
        assert backup_1[0].text == "version 2"

        # Third most recent backup (n=2) should be version 1 (oldest kept after rotation)
        backup_2 = storage.load_backup(n=2)
        assert backup_2[0].text == "version 1"

    def test_backup_rotation_default_is_three(self, tmp_path: Path) -> None:
        """Default max_backups should be 3."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save 5 times without specifying max_backups
        for i in range(5):
            todos = [Todo(id=1, text=f"version {i}")]
            storage.save(todos, backup_before_save=True)

        # Should have 3 backup files (default)
        backup_files = list(tmp_path.glob("todo.json.bak*"))
        assert len(backup_files) == 3, f"Expected 3 backup files by default, found {len(backup_files)}"


class TestLoadBackup:
    """Tests for load_backup() method."""

    def test_load_backup_returns_todos(self, tmp_path: Path) -> None:
        """load_backup(n=0) method returns todos from nth most recent backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save with backup
        todos = [Todo(id=1, text="backup content")]
        storage.save(todos, backup_before_save=True)

        # Modify and save again
        new_todos = [Todo(id=1, text="new content")]
        storage.save(new_todos, backup_before_save=True)

        # Load backup should return previous version
        backup_todos = storage.load_backup(n=0)
        assert len(backup_todos) == 1
        assert backup_todos[0].text == "backup content"

    def test_load_backup_raises_when_no_backup(self, tmp_path: Path) -> None:
        """load_backup() should raise when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save without backup
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Attempting to load backup should raise
        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.load_backup()

    def test_load_backup_raises_when_n_too_large(self, tmp_path: Path) -> None:
        """load_backup(n=X) should raise when X exceeds available backups."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save twice with backup
        storage.save([Todo(id=1, text="v1")], backup_before_save=True)
        storage.save([Todo(id=1, text="v2")], backup_before_save=True)

        # Requesting backup n=10 should fail (only 2 backups exist)
        with pytest.raises(FileNotFoundError, match=r"Backup .* not found"):
            storage.load_backup(n=10)


class TestRestoreFromBackup:
    """Tests for restore_backup() method."""

    def test_restore_from_backup_corrupted_file(self, tmp_path: Path) -> None:
        """Corrupt file, then restore from backup successfully."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save valid data with backup
        original_todos = [Todo(id=1, text="valid data")]
        storage.save(original_todos, backup_before_save=True)

        # Simulate new save (this creates backup of "valid data")
        storage.save([Todo(id=1, text="new data")], backup_before_save=True)

        # Corrupt the main file
        db.write_text("corrupted data {{{", encoding="utf-8")

        # Restore from backup (most recent backup is "valid data")
        storage.restore_backup()

        # Verify restoration worked - we should get the backup content
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "valid data"

    def test_restore_from_specific_backup(self, tmp_path: Path) -> None:
        """Restore from a specific backup (not the most recent)."""
        import time

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save multiple versions (each creates a backup of the previous)
        storage.save([Todo(id=1, text="v1")], backup_before_save=True)  # creates backup of nothing (first save)
        time.sleep(0.01)
        storage.save([Todo(id=1, text="v2")], backup_before_save=True)  # creates backup of "v1"
        time.sleep(0.01)
        storage.save([Todo(id=1, text="v3")], backup_before_save=True)  # creates backup of "v2"

        # Backups are: newest is "v2", second newest is "v1"
        # Restore from n=1 (second most recent, should be "v1")
        storage.restore_backup(n=1)

        loaded = storage.load()
        assert loaded[0].text == "v1"


class TestBackupIntegration:
    """Integration tests for backup functionality with TodoApp."""

    def test_backup_integration_with_cli(self, tmp_path: Path) -> None:
        """Backup should work seamlessly with CLI operations."""
        from flywheel.cli import TodoApp

        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Enable backups on the storage
        app.storage._backup_enabled = True
        app.storage._max_backups = 3

        # Add todos
        app.add("first todo")
        app.add("second todo")

        # Save with backup manually (simulating what would happen with backup enabled)
        todos = app._load()
        app.storage.save(todos, backup_before_save=True)

        # Remove a todo (destructive operation)
        app.remove(1)

        # Restore from backup
        app.storage.restore_backup()

        # Verify we got our todo back
        loaded = app.list()
        assert len(loaded) == 2
        assert any(t.text == "first todo" for t in loaded)
