"""Tests for automatic backup before save operations.

Issue #4766: Add automatic backup before save operations

This test suite verifies that:
1. save() creates a .bak file with previous content
2. The backup file is created atomically
3. A restore command recovers data from backup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.cli import main
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeSave:
    """Test automatic backup creation before save operations."""

    def test_save_creates_backup_file_with_previous_content(self, tmp_path: Path) -> None:
        """Test that save creates a .bak file containing previous content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save new data - this should create a backup
        new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
        storage.save(new_todos)

        # Verify backup file exists
        backup_path = db.with_suffix(".json.bak")
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup contains original content
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "original task"

    def test_backup_overwrites_previous_backup(self, tmp_path: Path) -> None:
        """Test that only the most recent backup is kept (no disk bloat)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="version 1")])

        # Second save
        storage.save([Todo(id=1, text="version 2")])

        # Third save
        storage.save([Todo(id=1, text="version 3")])

        # Should only have one backup file
        backup_path = db.with_suffix(".json.bak")
        assert backup_path.exists()

        # Backup should contain version 2 (the previous version)
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "version 2"

    def test_backup_not_created_on_first_save(self, tmp_path: Path) -> None:
        """Test that no backup is created when saving to a new file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - no previous data to backup
        storage.save([Todo(id=1, text="first save")])

        backup_path = db.with_suffix(".json.bak")
        assert not backup_path.exists(), "No backup should exist on first save"

    def test_restore_recovers_from_backup(self, tmp_path: Path) -> None:
        """Test that restore() recovers data from backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save original data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="tasks")]
        storage.save(original_todos)

        # Save new data (creates backup)
        storage.save([Todo(id=1, text="modified")])

        # Restore from backup
        restored_todos = storage.restore()

        # Verify restored data matches original
        assert len(restored_todos) == 2
        assert restored_todos[0].text == "original"
        assert restored_todos[1].text == "tasks"

    def test_restore_raises_error_when_no_backup(self, tmp_path: Path) -> None:
        """Test that restore raises FileNotFoundError when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # No backup exists
        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.restore()

    def test_restore_updates_main_file(self, tmp_path: Path) -> None:
        """Test that restore updates the main database file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save original
        storage.save([Todo(id=1, text="original")])

        # Modify (creates backup)
        storage.save([Todo(id=1, text="modified")])

        # Restore
        storage.restore()

        # Verify main file now contains original content
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "original"

    def test_backup_is_atomic(self, tmp_path: Path) -> None:
        """Test that backup file is created atomically (no partial writes)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        # Save new data
        storage.save([Todo(id=1, text="updated")])

        # Backup should be valid JSON
        backup_path = db.with_suffix(".json.bak")
        backup_content = backup_path.read_text(encoding="utf-8")

        # Should be parseable as JSON without errors
        parsed = json.loads(backup_content)
        assert isinstance(parsed, list)


class TestRestoreCLI:
    """Test the restore CLI subcommand."""

    def test_restore_cli_command(self, tmp_path: Path, capsys) -> None:
        """Test that 'todo restore' CLI command works."""
        db = tmp_path / "todo.json"

        # Add initial todo via CLI
        assert main(["--db", str(db), "add", "original task"]) == 0

        # Add another todo (modifies file, creates backup)
        assert main(["--db", str(db), "add", "new task"]) == 0

        # Remove first todo (modifies file, creates backup of 2-todo state)
        assert main(["--db", str(db), "rm", "1"]) == 0

        # Restore from backup (should restore 2-todo state)
        assert main(["--db", str(db), "restore"]) == 0

        # Verify restored content
        captured = capsys.readouterr()
        assert "Restored 2 todo(s)" in captured.out

    def test_restore_cli_shows_restored_todos(self, tmp_path: Path, capsys) -> None:
        """Test that restore command shows the restored todos."""
        db = tmp_path / "todo.json"

        # Add and then modify
        assert main(["--db", str(db), "add", "task one"]) == 0
        assert main(["--db", str(db), "add", "task two"]) == 0
        assert main(["--db", str(db), "rm", "1"]) == 0

        # Restore
        assert main(["--db", str(db), "restore"]) == 0

        captured = capsys.readouterr()
        assert "task one" in captured.out
        assert "task two" in captured.out

    def test_restore_cli_errors_when_no_backup(self, tmp_path: Path, capsys) -> None:
        """Test that restore CLI returns error when no backup exists."""
        db = tmp_path / "todo.json"

        # No backup exists, should fail
        result = main(["--db", str(db), "restore"])
        assert result == 1

        captured = capsys.readouterr()
        assert "No backup file found" in captured.err
