"""Tests for backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() can optionally create
a backup of the previous file before overwriting.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupFeature:
    """Tests for the backup=True parameter in save()."""

    def test_save_with_backup_creates_bak_file(self, tmp_path: Path) -> None:
        """Test that save(backup=True) creates a .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save with backup=True
        new_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
        storage.save(new_todos, backup=True)

        # Verify backup file was created (backup is db name + .bak)
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created when backup=True"

    def test_backup_contains_previous_content(self, tmp_path: Path) -> None:
        """Test that backup file contains the content from before the save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
        storage.save(original_todos)

        # Get original content for comparison
        original_content = db.read_text(encoding="utf-8")

        # Save with backup=True
        new_todos = [Todo(id=1, text="completely different")]
        storage.save(new_todos, backup=True)

        # Verify backup contains the original content
        backup_path = tmp_path / "todo.json.bak"
        backup_content = backup_path.read_text(encoding="utf-8")
        assert backup_content == original_content, (
            "Backup file should contain previous content"
        )

        # Verify the main file has new content
        main_content = db.read_text(encoding="utf-8")
        assert main_content != original_content, "Main file should have new content"

    def test_backup_file_permissions_match_main_file(self, tmp_path: Path) -> None:
        """Test that backup file has same permissions as main file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Save with backup=True
        new_todos = [Todo(id=1, text="updated")]
        storage.save(new_todos, backup=True)

        # Get file permissions
        main_stat = db.stat()
        backup_path = tmp_path / "todo.json.bak"
        backup_stat = backup_path.stat()

        # Compare permission bits (focus on user permissions which we control)
        main_mode = stat.S_IMODE(main_stat.st_mode)
        backup_mode = stat.S_IMODE(backup_stat.st_mode)

        assert main_mode == backup_mode, (
            f"Backup file permissions ({oct(backup_mode)}) should match "
            f"main file permissions ({oct(main_mode)})"
        )

    def test_backup_overwrites_previous_backup(self, tmp_path: Path) -> None:
        """Test that multiple saves with backup overwrite the previous backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first")]
        storage.save(first_todos)

        # Second save with backup
        second_todos = [Todo(id=1, text="second")]
        storage.save(second_todos, backup=True)

        # Third save with backup
        third_todos = [Todo(id=1, text="third")]
        storage.save(third_todos, backup=True)

        # Backup should contain second content (the one before third save)
        backup_path = tmp_path / "todo.json.bak"
        backup_content = backup_path.read_text(encoding="utf-8")
        second_content = json.dumps([t.to_dict() for t in second_todos], ensure_ascii=False, indent=2)

        assert backup_content == second_content, (
            "Backup should contain content from second-to-last save"
        )

    def test_save_without_backup_does_not_create_bak(self, tmp_path: Path) -> None:
        """Test that save() without backup parameter does not create .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        first_todos = [Todo(id=1, text="first")]
        storage.save(first_todos)

        # Save without backup (default)
        second_todos = [Todo(id=1, text="second")]
        storage.save(second_todos)

        # Verify no backup file was created
        backup_path = tmp_path / ".todo.json.bak"
        assert not backup_path.exists(), (
            "Backup file should NOT be created when backup is not specified"
        )

    def test_backup_false_does_not_create_bak(self, tmp_path: Path) -> None:
        """Test that save(backup=False) does not create .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        first_todos = [Todo(id=1, text="first")]
        storage.save(first_todos)

        # Save with backup=False
        second_todos = [Todo(id=1, text="second")]
        storage.save(second_todos, backup=False)

        # Verify no backup file was created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), (
            "Backup file should NOT be created when backup=False"
        )

    def test_backup_on_first_save(self, tmp_path: Path) -> None:
        """Test that backup on first save (no existing file) works correctly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save with backup (no existing file to backup)
        todos = [Todo(id=1, text="first")]
        storage.save(todos, backup=True)

        # Backup should not exist since there was nothing to backup
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), (
            "Backup should not be created when no previous file exists"
        )

        # Main file should still be created correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "first"

    def test_backup_preserves_unicode_content(self, tmp_path: Path) -> None:
        """Test that backup correctly preserves unicode content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data with unicode
        unicode_todos = [Todo(id=1, text="中文任务"), Todo(id=2, text="émoji 🎉")]
        storage.save(unicode_todos)

        # Save with backup
        new_todos = [Todo(id=1, text="updated")]
        storage.save(new_todos, backup=True)

        # Verify backup preserves unicode
        backup_path = tmp_path / "todo.json.bak"
        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))

        assert backup_data[0]["text"] == "中文任务"
        assert backup_data[1]["text"] == "émoji 🎉"
