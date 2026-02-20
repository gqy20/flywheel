"""Tests for optional auto-backup mechanism in TodoStorage.

This test suite verifies the backup feature for issue #4667:
- save() supports backup=True parameter to create .bak file
- backup file has same permissions as original (0600)
- backup can be disabled via backup=False parameter
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestAutoBackup:
    """Tests for auto-backup functionality."""

    def test_save_with_backup_true_creates_backup_file(self, tmp_path: Path) -> None:
        """Test that save(backup=True) creates a .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save again with backup=True
        new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
        storage.save(new_todos, backup=True)

        # Backup file should exist
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"

    def test_backup_file_contains_original_content(self, tmp_path: Path) -> None:
        """Test that backup file contains the original file content before overwrite."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="second")]
        storage.save(original_todos)

        # Save again with backup=True
        new_todos = [Todo(id=1, text="modified task")]
        storage.save(new_todos, backup=True)

        # Backup file should contain original content
        backup_path = tmp_path / "todo.json.bak"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))

        assert len(backup_content) == 2
        assert backup_content[0]["text"] == "original task"
        assert backup_content[1]["text"] == "second"

    def test_backup_file_has_restrictive_permissions(self, tmp_path: Path) -> None:
        """Test that backup file has 0600 permissions (owner read/write only)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Save again with backup=True
        storage.save([Todo(id=1, text="modified")], backup=True)

        # Check backup file permissions
        backup_path = tmp_path / "todo.json.bak"
        file_stat = backup_path.stat()
        permissions = stat.S_IMODE(file_stat.st_mode)

        assert permissions == stat.S_IRUSR | stat.S_IWUSR, (
            f"Backup file should have 0600 permissions, got {oct(permissions)}"
        )

    def test_save_without_backup_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that save(backup=False) does not create backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Save again with backup=False (default)
        storage.save([Todo(id=1, text="modified")], backup=False)

        # Backup file should NOT exist
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup file should not be created with backup=False"

    def test_save_default_no_backup_for_backwards_compatibility(self, tmp_path: Path) -> None:
        """Test that save() without backup param defaults to no backup (backwards compatible)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Save again without backup parameter
        storage.save([Todo(id=1, text="modified")])

        # Backup file should NOT exist by default
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup should be disabled by default for backwards compatibility"

    def test_backup_overwrites_existing_backup(self, tmp_path: Path) -> None:
        """Test that multiple saves with backup only keep the latest backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="version1")])
        storage.save([Todo(id=1, text="version2")], backup=True)
        storage.save([Todo(id=1, text="version3")], backup=True)

        # Backup should contain version2 (the content before version3)
        backup_path = tmp_path / "todo.json.bak"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))

        assert backup_content[0]["text"] == "version2"

    def test_backup_without_existing_file_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that backup=True on first save (no existing file) doesn't create backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save with backup=True - no existing file to backup
        storage.save([Todo(id=1, text="first")], backup=True)

        # Backup file should NOT exist since there was no original file
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "No backup should be created when there's no existing file"
