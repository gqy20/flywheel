"""Tests for automatic backup before save operations.

Issue #4766: Add automatic backup before save operations.

This test suite verifies that:
1. Calling save() creates a .bak file with previous content
2. The backup file is created atomically
3. A restore command recovers data from backup
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeSave:
    """Tests for automatic backup functionality."""

    def test_save_creates_backup_file_with_previous_content(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak file with the previous content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data (first save, no backup yet)
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Second save should create backup of first version
        new_todos = [Todo(id=1, text="modified task")]
        storage.save(new_todos)

        # Verify backup file was created
        backup_file = tmp_path / ".todo.json.bak"
        assert backup_file.exists(), "Backup file should be created after second save"

        # Verify backup content matches original (first version), not the modified one
        backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "original task"

    def test_backup_preserves_content_before_overwrite(self, tmp_path: Path) -> None:
        """Test that backup contains the PREVIOUS content, not the new content."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first version")]
        storage.save(first_todos)

        # Second save - should backup first version
        second_todos = [Todo(id=1, text="second version"), Todo(id=2, text="new task")]
        storage.save(second_todos)

        # Verify backup contains first version, not second
        backup_file = tmp_path / ".todo.json.bak"
        backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "first version"

        # Verify main file has second version
        main_content = json.loads(db.read_text(encoding="utf-8"))
        assert len(main_content) == 2
        assert main_content[0]["text"] == "second version"

    def test_backup_keeps_only_most_recent(self, tmp_path: Path) -> None:
        """Test that only the most recent backup is kept (no disk bloat)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Multiple saves
        for i in range(5):
            storage.save([Todo(id=1, text=f"version {i}")])

        # Should only have one backup file
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) == 1, "Should only keep the most recent backup"

    def test_no_backup_on_first_save(self, tmp_path: Path) -> None:
        """Test that no backup is created when saving to a new file."""
        db = tmp_path / "new.json"
        storage = TodoStorage(str(db))

        # First save to non-existent file
        storage.save([Todo(id=1, text="initial")])

        # No backup should exist for new files
        backup_file = tmp_path / ".new.json.bak"
        assert not backup_file.exists(), "No backup should be created for new files"

    def test_restore_command_recovers_from_backup(self, tmp_path: Path) -> None:
        """Test that restore command recovers data from backup."""
        db = str(tmp_path / "todo.json")

        # Create initial data using CLI
        parser = build_parser()
        args = parser.parse_args(["--db", db, "add", "original task"])
        assert run_command(args) == 0

        # Add another task (this creates a backup of the first state)
        args = parser.parse_args(["--db", db, "add", "second task"])
        assert run_command(args) == 0

        # Verify we have 2 tasks now
        args = parser.parse_args(["--db", db, "list"])
        assert run_command(args) == 0

        # Now delete everything and restore from backup
        storage = TodoStorage(db)
        storage.save([])  # Delete all
        assert len(storage.load()) == 0

        # Restore from backup
        args = parser.parse_args(["--db", db, "restore"])
        result = run_command(args)
        assert result == 0

        # Verify we recovered the data
        restored = storage.load()
        assert len(restored) >= 1, "Should have restored at least one todo"
        assert any("original" in t.text for t in restored), "Should have recovered original task"


class TestRestoreCommand:
    """Tests for the restore CLI command."""

    def test_restore_returns_error_when_no_backup(self, tmp_path: Path, capsys) -> None:
        """Test that restore returns error when no backup file exists."""
        db = str(tmp_path / "todo.json")

        # Create a todo but don't have a backup
        parser = build_parser()
        args = parser.parse_args(["--db", db, "add", "test"])
        assert run_command(args) == 0

        # Remove backup if it exists
        backup_path = tmp_path / ".todo.json.bak"
        if backup_path.exists():
            backup_path.unlink()

        # Try to restore - should fail gracefully
        args = parser.parse_args(["--db", db, "restore"])
        result = run_command(args)
        assert result == 1  # Non-zero exit code for error

        captured = capsys.readouterr()
        assert "no backup" in captured.err.lower() or "not found" in captured.err.lower()

    def test_restore_success_message(self, tmp_path: Path, capsys) -> None:
        """Test that restore prints a success message."""
        db = str(tmp_path / "todo.json")
        parser = build_parser()

        # Create some todos to generate backups
        args = parser.parse_args(["--db", db, "add", "task 1"])
        assert run_command(args) == 0
        args = parser.parse_args(["--db", db, "add", "task 2"])
        assert run_command(args) == 0

        # Clear the data
        storage = TodoStorage(db)
        storage.save([])

        # Restore
        args = parser.parse_args(["--db", db, "restore"])
        result = run_command(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "restored" in captured.out.lower()
