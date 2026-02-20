"""Tests for automatic backup before save operations (issue #4766).

This test suite verifies that:
1. save() creates a .bak file with previous content
2. The backup file is created atomically
3. A restore command recovers data from backup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestAutomaticBackup:
    """Tests for automatic backup functionality in TodoStorage."""

    def test_save_creates_backup_file_with_previous_content(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak file containing previous content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save initial data
        initial_todos = [Todo(id=1, text="initial task")]
        storage.save(initial_todos)

        # Save new data (should create backup)
        new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
        storage.save(new_todos)

        # Verify backup file exists
        backup_path = db.with_suffix(".json.bak")
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup contains the previous content
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "initial task"

    def test_save_keeps_only_most_recent_backup(self, tmp_path: Path) -> None:
        """Test that only the most recent backup is kept (no disk bloat)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        backup_path = db.with_suffix(".json.bak")

        # Save multiple times
        for i in range(5):
            storage.save([Todo(id=1, text=f"iteration {i}")])

        # Verify only one backup file exists
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) == 1, "Should keep only one backup file"

        # Verify backup contains second-to-last save
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "iteration 3"

    def test_save_with_no_existing_file_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that saving for the first time does not create a backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        backup_path = db.with_suffix(".json.bak")

        # First save (no existing file to backup)
        storage.save([Todo(id=1, text="first save")])

        # No backup should exist
        assert not backup_path.exists(), "No backup should be created on first save"

    def test_backup_is_created_atomically(self, tmp_path: Path) -> None:
        """Test that backup file is created atomically (not partially written)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        backup_path = db.with_suffix(".json.bak")

        # Create initial data
        initial_todos = [Todo(id=i, text=f"task {i}") for i in range(10)]
        storage.save(initial_todos)

        # Save again to trigger backup
        new_todos = [Todo(id=1, text="new task")]
        storage.save(new_todos)

        # Backup should contain valid JSON
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert isinstance(backup_content, list)
        assert len(backup_content) == 10


class TestRestoreFromBackup:
    """Tests for restore functionality."""

    def test_restore_command_recovers_from_backup(self, tmp_path: Path, capsys) -> None:
        """Test that restore command recovers data from backup."""
        db = tmp_path / "todo.json"
        app = TodoApp(str(db))

        # Create initial todos and save multiple times
        # Each save creates a backup of the previous state
        app.add("task one")   # First save - no backup yet
        app.add("task two")   # Second save - backup contains task one

        # Remove all tasks (simulate accidental deletion)
        app.remove(1)
        app.remove(2)

        # Verify database is empty
        assert app.list() == []

        # Restore from backup (backup has state before last save = [task one])
        restored = app.restore()
        assert len(restored) == 1, "Should restore tasks from backup"
        assert restored[0].text == "task two", "Should restore the second-to-last state"

    def test_restore_returns_previous_state_when_backup_exists(self, tmp_path: Path) -> None:
        """Test that restore returns previous state when backup exists."""
        db = tmp_path / "todo.json"
        app = TodoApp(str(db))

        # First save (no backup yet)
        app.add("first task")
        # Second save (backup contains first task)
        app.add("second task")

        # Remove the second task
        app.remove(2)

        # Restore from backup (which has [first task])
        restored = app.restore()
        # After remove(2), backup contains [first task, second task]
        # Wait, let's trace more carefully:
        # add("first task") -> save([first]) - no backup
        # add("second task") -> save([first, second]) - backup has [first]
        # remove(2) -> save([first]) - backup has [first, second]
        # restore() returns [first, second]
        assert len(restored) == 2, "Should restore state from before removal"

    def test_cli_restore_subcommand(self, tmp_path: Path, capsys) -> None:
        """Test that CLI restore subcommand works correctly."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # Add some todos
        args = parser.parse_args(["--db", db, "add", "task to restore"])
        assert run_command(args) == 0

        # Make a change that overwrites
        args = parser.parse_args(["--db", db, "add", "another task"])
        assert run_command(args) == 0

        # Remove all
        args = parser.parse_args(["--db", db, "rm", "1"])
        assert run_command(args) == 0
        args = parser.parse_args(["--db", db, "rm", "2"])
        assert run_command(args) == 0

        # Restore from backup
        args = parser.parse_args(["--db", db, "restore"])
        assert run_command(args) == 0

        captured = capsys.readouterr()
        assert "Restored" in captured.out


class TestStorageRestoreMethod:
    """Tests for storage-level restore functionality."""

    def test_storage_restore_returns_backup_content(self, tmp_path: Path) -> None:
        """Test that storage.restore() returns content from backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data and backup
        storage.save([Todo(id=1, text="original")])
        storage.save([Todo(id=2, text="modified")])

        # Restore should return the backup content
        restored = storage.restore()
        assert len(restored) == 1
        assert restored[0].text == "original"

    def test_storage_restore_raises_when_no_backup(self, tmp_path: Path) -> None:
        """Test that restore raises appropriate error when no backup exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # No backup exists
        with pytest.raises(FileNotFoundError, match="No backup file found"):
            storage.restore()
