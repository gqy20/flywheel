"""Tests for file backup before save operation.

This test suite verifies that TodoStorage.save() creates a backup file
before overwriting the original file, allowing recovery from data loss.

Issue #5559: Add file backup before save operation
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeSave:
    """Test cases for backup functionality in TodoStorage.save()."""

    def test_save_creates_backup_of_existing_file(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak backup of the existing file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Verify original content
        original_content = db.read_text(encoding="utf-8")

        # Save new data
        new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
        storage.save(new_todos)

        # Check backup file exists and contains original content
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"
        assert backup_path.read_text(encoding="utf-8") == original_content

    def test_first_save_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that saving a new file (no existing file) does not create backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no existing file
        todos = [Todo(id=1, text="first task")]
        storage.save(todos)

        # No backup should be created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup should not be created on first save"

    def test_backup_disabled_with_backup_false(self, tmp_path: Path) -> None:
        """Test that backup can be disabled via backup=False constructor parameter."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=False)

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Save new data
        new_todos = [Todo(id=1, text="modified")]
        storage.save(new_todos)

        # No backup should be created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup should not be created when backup=False"

    def test_backup_contains_old_data(self, tmp_path: Path) -> None:
        """Test that backup file contains the old data, not new data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data with specific content
        original_todos = [
            Todo(id=1, text="task one"),
            Todo(id=2, text="task two"),
            Todo(id=3, text="task three"),
        ]
        storage.save(original_todos)

        # Save completely different data
        new_todos = [Todo(id=10, text="completely different")]
        storage.save(new_todos)

        # Backup should contain original data
        backup_path = tmp_path / "todo.json.bak"
        backup_storage = TodoStorage(str(backup_path))
        backup_todos = backup_storage.load()

        assert len(backup_todos) == 3
        assert backup_todos[0].text == "task one"
        assert backup_todos[1].text == "task two"
        assert backup_todos[2].text == "task three"

    def test_backup_overwrites_previous_backup(self, tmp_path: Path) -> None:
        """Test that each save overwrites the previous backup with current state."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="version 1")])

        # Second save
        storage.save([Todo(id=1, text="version 2")])
        backup_path = tmp_path / "todo.json.bak"
        backup_storage = TodoStorage(str(backup_path))
        assert backup_storage.load()[0].text == "version 1"

        # Third save
        storage.save([Todo(id=1, text="version 3")])
        # Backup should now contain version 2, not version 1
        backup_todos = backup_storage.load()
        assert backup_todos[0].text == "version 2"
