"""Tests for file backup/rotation feature (Issue #2597).

This test suite verifies that TodoStorage creates backups before overwriting
existing data, with proper rotation and configurable options.
"""
from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for basic backup file creation."""

    def test_backup_created_when_overwriting_existing_file(self, tmp_path) -> None:
        """Test that .bak file is created when overwriting existing data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Overwrite with new data
        new_todos = [Todo(id=1, text="modified task")]
        storage.save(new_todos)

        # Verify backup was created
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup contains original data
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "original task"

    def test_no_backup_created_for_new_file(self, tmp_path) -> None:
        """Test that no backup is created when file doesn't exist yet."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no file exists yet
        todos = [Todo(id=1, text="first task")]
        storage.save(todos)

        # Verify no backup was created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "No backup should be created for new file"


class TestBackupRotation:
    """Tests for backup rotation keeping only last N backups."""

    def test_backup_rotation_keeps_last_3_backups(self, tmp_path) -> None:
        """Test that backup rotation keeps only the last 3 backups."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="version-0")])

        # Perform multiple saves to trigger rotation
        for i in range(1, 6):
            storage.save([Todo(id=1, text=f"version-{i}")])

        # Verify only .bak, .bak1, .bak2 exist (last 3)
        backup = tmp_path / "todo.json.bak"
        backup1 = tmp_path / "todo.json.bak1"
        backup2 = tmp_path / "todo.json.bak2"
        backup3 = tmp_path / "todo.json.bak3"

        assert backup.exists(), "Latest backup .bak should exist"
        assert backup1.exists(), "Backup .bak1 should exist"
        assert backup2.exists(), "Backup .bak2 should exist"
        assert not backup3.exists(), "Old backup .bak3 should be deleted"

        # Verify backup content order (newest in .bak)
        bak_content = json.loads(backup.read_text(encoding="utf-8"))
        bak1_content = json.loads(backup1.read_text(encoding="utf-8"))
        bak2_content = json.loads(backup2.read_text(encoding="utf-8"))

        assert bak_content[0]["text"] == "version-4"
        assert bak1_content[0]["text"] == "version-3"
        assert bak2_content[0]["text"] == "version-2"

    def test_rotation_with_custom_max_backups(self, tmp_path) -> None:
        """Test that rotation respects custom max_backups setting."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), max_backups=2)

        # Create initial data
        storage.save([Todo(id=1, text="version-0")])

        # Perform multiple saves
        for i in range(1, 5):
            storage.save([Todo(id=1, text=f"version-{i}")])

        # Verify only .bak and .bak1 exist (max 2)
        backup = tmp_path / "todo.json.bak"
        backup1 = tmp_path / "todo.json.bak1"
        backup2 = tmp_path / "todo.json.bak2"

        assert backup.exists(), "Latest backup .bak should exist"
        assert backup1.exists(), "Backup .bak1 should exist"
        assert not backup2.exists(), ".bak2 should not exist with max_backups=2"


class TestBackupPermissions:
    """Tests for backup file permissions."""

    def test_backup_has_restrictive_permissions(self, tmp_path) -> None:
        """Test that backup files have 0o600 permissions (rw-------)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and overwrite
        storage.save([Todo(id=1, text="original")])
        storage.save([Todo(id=1, text="modified")])

        # Check backup permissions
        backup_path = tmp_path / "todo.json.bak"
        backup_stat = backup_path.stat()
        backup_mode = backup_stat.st_mode & 0o777

        assert backup_mode == 0o600, f"Backup should have 0o600 permissions, got {oct(backup_mode)}"


class TestBackupContentValidity:
    """Tests for backup file content validity."""

    def test_backup_contains_valid_json(self, tmp_path) -> None:
        """Test that backup contains valid JSON that can be loaded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create original todos with various content
        original_todos = [
            Todo(id=1, text="task with unicode: 你好"),
            Todo(id=2, text='task with "quotes"', done=True),
            Todo(id=3, text="task with \\n newline"),
        ]
        storage.save(original_todos)

        # Overwrite
        storage.save([Todo(id=1, text="new task")])

        # Load backup and verify it's valid
        backup_path = tmp_path / "todo.json.bak"
        backup_storage = TodoStorage(str(backup_path))
        loaded_todos = backup_storage.load()

        assert len(loaded_todos) == 3
        assert loaded_todos[0].text == "task with unicode: 你好"
        assert loaded_todos[1].text == 'task with "quotes"'
        assert loaded_todos[1].done is True
        assert loaded_todos[2].text == "task with \\n newline"

    def test_backup_matches_previous_state(self, tmp_path) -> None:
        """Test that backup exactly matches the state before overwrite."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create specific state
        original_todos = [
            Todo(id=1, text="task1", done=False),
            Todo(id=2, text="task2", done=True),
        ]
        storage.save(original_todos)

        # Get the exact JSON content
        original_json = db.read_text(encoding="utf-8")

        # Overwrite
        storage.save([Todo(id=1, text="modified")])

        # Verify backup matches original
        backup_path = tmp_path / "todo.json.bak"
        backup_json = backup_path.read_text(encoding="utf-8")

        assert backup_json == original_json, "Backup should exactly match previous state"


class TestBackupFailureHandling:
    """Tests for graceful handling of backup failures."""

    def test_backup_failure_doesnt_prevent_main_save(self, tmp_path) -> None:
        """Test that if backup creation fails, main save still succeeds."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial file
        storage.save([Todo(id=1, text="original")])

        # Make backup directory read-only to simulate backup failure
        backup_path = tmp_path / "todo.json.bak"
        # Create a directory with the backup name to trigger failure
        backup_path.mkdir()

        # This should not raise an error even though backup fails
        storage.save([Todo(id=1, text="modified")])

        # Verify main save succeeded
        content = json.loads(db.read_text(encoding="utf-8"))
        assert content[0]["text"] == "modified"


class TestNoBackupFlag:
    """Tests for --no-backup functionality."""

    def test_no_backup_when_disabled(self, tmp_path) -> None:
        """Test that no backup is created when backup is disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=False)

        # Create and overwrite
        storage.save([Todo(id=1, text="original")])
        storage.save([Todo(id=1, text="modified")])

        # Verify no backup was created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "No backup should be created when disabled"
