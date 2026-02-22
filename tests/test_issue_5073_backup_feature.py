"""Tests for backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() can optionally create
a backup of the previous file before overwriting, allowing data recovery.

Issue: #5073 - Add data backup functionality
"""

from __future__ import annotations

import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupFeature:
    """Test backup functionality in TodoStorage.save()."""

    def test_backup_false_by_default(self, tmp_path: Path) -> None:
        """Test that backup is disabled by default (backward compatibility)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        todos1 = [Todo(id=1, text="first")]
        storage.save(todos1)

        # Second save (no backup should be created)
        todos2 = [Todo(id=1, text="second")]
        storage.save(todos2)

        # No backup file should exist
        backup_path = tmp_path / ".todo.json.bak"
        assert not backup_path.exists()

    def test_backup_true_creates_bak_file(self, tmp_path: Path) -> None:
        """Test that backup=True creates .bak file when previous file exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save (creates initial file)
        todos1 = [Todo(id=1, text="first"), Todo(id=2, text="initial data")]
        storage.save(todos1)

        # Second save with backup enabled
        todos2 = [Todo(id=1, text="second")]
        storage.save(todos2, backup=True)

        # Backup file should exist
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"

    def test_backup_file_content_matches_original(self, tmp_path: Path) -> None:
        """Test that backup file contains the previous version's content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        original_todos = [
            Todo(id=1, text="original task"),
            Todo(id=2, text="another task"),
        ]
        storage.save(original_todos)

        # Get original content
        original_content = db.read_text(encoding="utf-8")

        # Second save with backup
        new_todos = [Todo(id=1, text="replaced task")]
        storage.save(new_todos, backup=True)

        # Backup should contain original content
        backup_path = tmp_path / "todo.json.bak"
        backup_content = backup_path.read_text(encoding="utf-8")

        assert backup_content == original_content, (
            "Backup file should contain the previous version's content"
        )

        # Main file should contain new content
        new_content = db.read_text(encoding="utf-8")
        assert new_content != original_content
        assert "replaced task" in new_content

    def test_backup_file_permissions_match_original(self, tmp_path: Path) -> None:
        """Test that backup file has same permissions as original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        todos1 = [Todo(id=1, text="first")]
        storage.save(todos1)

        # Get original file permissions
        original_mode = db.stat().st_mode

        # Second save with backup
        todos2 = [Todo(id=1, text="second")]
        storage.save(todos2, backup=True)

        # Backup file should have same permissions
        backup_path = tmp_path / "todo.json.bak"
        backup_mode = backup_path.stat().st_mode

        # Compare permission bits (ignore file type flags)
        assert stat.S_IMODE(backup_mode) == stat.S_IMODE(original_mode), (
            "Backup file should have same permissions as original"
        )

    def test_first_save_with_backup_no_error(self, tmp_path: Path) -> None:
        """Test that first save with backup=True doesn't fail (no previous file)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save with backup (no previous file exists)
        todos = [Todo(id=1, text="first")]
        storage.save(todos, backup=True)

        # File should be created successfully
        assert db.exists()

        # No backup file should be created (nothing to backup)
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()

    def test_backup_overwrites_existing_backup(self, tmp_path: Path) -> None:
        """Test that multiple saves with backup overwrite the previous backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="v1")])

        # Second save with backup
        storage.save([Todo(id=1, text="v2")], backup=True)
        backup_path = tmp_path / "todo.json.bak"
        assert "v1" in backup_path.read_text()

        # Third save with backup
        storage.save([Todo(id=1, text="v3")], backup=True)

        # Backup should now contain v2 (not v1)
        backup_content = backup_path.read_text()
        assert "v2" in backup_content
        assert "v1" not in backup_content

        # Main file should contain v3
        main_content = db.read_text()
        assert "v3" in main_content

    def test_backup_preserves_unicode_content(self, tmp_path: Path) -> None:
        """Test that backup correctly preserves unicode content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save with unicode content
        unicode_todos = [
            Todo(id=1, text="中文任务"),
            Todo(id=2, text="日本語タスク"),
            Todo(id=3, text="한국어 작업"),
        ]
        storage.save(unicode_todos)

        original_content = db.read_text(encoding="utf-8")

        # Save with backup
        storage.save([Todo(id=1, text="english")], backup=True)

        # Backup should preserve unicode correctly
        backup_path = tmp_path / "todo.json.bak"
        backup_content = backup_path.read_text(encoding="utf-8")

        assert backup_content == original_content
        assert "中文任务" in backup_content
        assert "日本語タスク" in backup_content
        assert "한국어 작업" in backup_content

    def test_backup_with_custom_db_path(self, tmp_path: Path) -> None:
        """Test that backup works with custom database path."""
        custom_path = tmp_path / "subdir" / "custom_db.json"
        storage = TodoStorage(str(custom_path))

        # First save
        storage.save([Todo(id=1, text="first")])

        # Second save with backup
        storage.save([Todo(id=1, text="second")], backup=True)

        # Backup should be in same directory as db
        backup_path = tmp_path / "subdir" / "custom_db.json.bak"
        assert backup_path.exists()
        assert "first" in backup_path.read_text()
