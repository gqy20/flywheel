"""Tests for optional backup mechanism in TodoStorage.save().

Issue #4667: Add optional automatic backup mechanism to prevent data loss.

This test suite verifies that:
1. save() supports backup=True parameter to create .bak file
2. Backup file permissions match original file (0600)
3. Backup can be disabled via configuration
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupMechanism:
    """Tests for backup feature in save()."""

    def test_save_with_backup_creates_backup_file(self, tmp_path: Path) -> None:
        """Test that save(backup=True) creates a .bak file before overwriting."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos, backup=True)

        # Backup file should not exist yet (no previous file to backup)
        backup_path = db.with_suffix(".json.bak")
        assert not backup_path.exists()

        # Save again with backup - should create backup of original
        new_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
        storage.save(new_todos, backup=True)

        # Backup file should now exist
        assert backup_path.exists()

        # Backup should contain the original data
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "original task"

    def test_save_without_backup_no_backup_file(self, tmp_path: Path) -> None:
        """Test that save(backup=False) does not create a .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save again without backup
        new_todos = [Todo(id=1, text="updated task")]
        storage.save(new_todos, backup=False)

        # Backup file should not exist
        backup_path = db.with_suffix(".json.bak")
        assert not backup_path.exists()

    def test_backup_file_has_same_permissions_as_original(self, tmp_path: Path) -> None:
        """Test that backup file permissions match original file (0600)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos, backup=True)

        # Verify original file has 0600 permissions
        original_mode = db.stat().st_mode & 0o777
        assert original_mode == 0o600, f"Original file should have 0600 perms, got {oct(original_mode)}"

        # Save again with backup
        new_todos = [Todo(id=1, text="updated task")]
        storage.save(new_todos, backup=True)

        # Check backup file permissions
        backup_path = db.with_suffix(".json.bak")
        assert backup_path.exists()

        backup_mode = backup_path.stat().st_mode & 0o777
        assert backup_mode == 0o600, f"Backup file should have 0600 perms, got {oct(backup_mode)}"

    def test_backup_content_matches_original_before_save(self, tmp_path: Path) -> None:
        """Test that backup file content matches the file content before save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data with specific content
        todos_v1 = [Todo(id=1, text="version 1"), Todo(id=2, text="task 2")]
        storage.save(todos_v1, backup=True)
        original_content = db.read_text(encoding="utf-8")

        # Save new version with backup
        todos_v2 = [Todo(id=1, text="version 2"), Todo(id=2, text="task 2"), Todo(id=3, text="task 3")]
        storage.save(todos_v2, backup=True)

        # Backup should contain exact content of v1
        backup_path = db.with_suffix(".json.bak")
        backup_content = backup_path.read_text(encoding="utf-8")
        assert backup_content == original_content

    def test_multiple_saves_with_backup_overwrites_previous_backup(self, tmp_path: Path) -> None:
        """Test that multiple saves with backup=True only keeps the latest backup.

        Per the issue: "可限制备份数量（如保留最近 3 个）避免磁盘占用过多"
        This implementation keeps only one backup (the previous version).
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create v1
        storage.save([Todo(id=1, text="v1")], backup=True)

        # Create v2 - backup should be v1
        storage.save([Todo(id=1, text="v2")], backup=True)
        backup_path = db.with_suffix(".json.bak")
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "v1"

        # Create v3 - backup should be v2
        storage.save([Todo(id=1, text="v3")], backup=True)
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "v2"

    def test_backup_default_is_false_for_backward_compatibility(self, tmp_path: Path) -> None:
        """Test that backup defaults to False for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data without explicit backup param
        storage.save([Todo(id=1, text="first")])

        # Save again without explicit backup param
        storage.save([Todo(id=1, text="second")])

        # No backup should exist
        backup_path = db.with_suffix(".json.bak")
        assert not backup_path.exists()

    def test_backup_works_with_unicode_content(self, tmp_path: Path) -> None:
        """Test that backup correctly preserves unicode content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create data with unicode
        unicode_todos = [Todo(id=1, text="你好世界"), Todo(id=2, text="日本語テスト")]
        storage.save(unicode_todos, backup=True)

        # Save again to create backup
        storage.save([Todo(id=1, text="updated")], backup=True)

        # Backup should have correct unicode
        backup_path = db.with_suffix(".json.bak")
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "你好世界"
        assert backup_data[1]["text"] == "日本語テスト"
