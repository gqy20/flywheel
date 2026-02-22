"""Tests for issue #5179: File backup before save feature.

This test suite verifies that TodoStorage.save() can optionally backup
existing files before overwriting them to prevent data loss from user errors.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupDisabled:
    """Tests for default behavior when backup is disabled (default)."""

    def test_no_backup_file_created_by_default(self, tmp_path: Path) -> None:
        """Verify backup=False (default) does not create a .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Save again with updated data
        todos[0].rename("updated")
        storage.save(todos)

        # No .bak file should exist
        assert not (tmp_path / "todo.json.bak").exists()

    def test_save_without_backup_works_normally(self, tmp_path: Path) -> None:
        """Verify save() works normally when backup=False."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos, backup=False)

        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"


class TestBackupEnabled:
    """Tests for backup behavior when backup=True."""

    def test_backup_file_created_when_backup_true(self, tmp_path: Path) -> None:
        """Verify backup=True creates a .bak file with old content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original content")]
        storage.save(original_todos)

        # Save again with backup enabled
        new_todos = [Todo(id=1, text="updated content")]
        storage.save(new_todos, backup=True)

        # Backup file should exist
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists()

        # Backup should contain original content
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_data) == 1
        assert backup_data[0]["text"] == "original content"

    def test_backup_preserves_original_file_permissions(self, tmp_path: Path) -> None:
        """Verify backup file has same permissions as original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data with specific permissions
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Get original permissions
        original_mode = db.stat().st_mode

        # Save with backup
        storage.save([Todo(id=1, text="updated")], backup=True)

        # Backup should have same permissions
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.stat().st_mode == original_mode

    def test_first_save_with_backup_no_error(self, tmp_path: Path) -> None:
        """Verify first save (no existing file) with backup=True doesn't error."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save with backup should not raise error
        todos = [Todo(id=1, text="first save")]
        storage.save(todos, backup=True)

        # File should exist
        assert db.exists()

        # No backup file since there was nothing to backup
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()

    def test_multiple_saves_with_backup_overwrites_old_backup(
        self, tmp_path: Path
    ) -> None:
        """Verify multiple saves with backup overwrite the previous backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="v1")])

        # Second save with backup
        storage.save([Todo(id=1, text="v2")], backup=True)

        # Third save with backup
        storage.save([Todo(id=1, text="v3")], backup=True)

        # Backup should contain v2 (the content before v3)
        backup_path = tmp_path / "todo.json.bak"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "v2"

        # Current file should contain v3
        current_data = json.loads(db.read_text(encoding="utf-8"))
        assert current_data[0]["text"] == "v3"

    def test_backup_with_unicode_content(self, tmp_path: Path) -> None:
        """Verify backup works correctly with unicode content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data with unicode
        storage.save([Todo(id=1, text="中文测试 🎉 emoji")])

        # Save with backup
        storage.save([Todo(id=1, text="updated 中文")], backup=True)

        # Backup should preserve unicode content
        backup_path = tmp_path / "todo.json.bak"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_data[0]["text"] == "中文测试 🎉 emoji"
