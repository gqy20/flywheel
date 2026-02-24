"""Tests for file backup before save operation.

This test suite verifies that TodoStorage.save() creates a backup file
before overwriting existing data, enabling recovery if new data is problematic.

Issue: #5559
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path: Path) -> None:
    """Test that save() creates a .bak backup file if original file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates initial file
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Second save - should create backup of original
    new_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
    storage.save(new_todos)

    # Backup file should exist
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Backup should contain original data
    backup_content = backup_path.read_text(encoding="utf-8")
    assert "original task" in backup_content
    assert "modified task" not in backup_content


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that saving a new file (no prior content) does not create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no original file exists
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # No backup should be created for first save
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created for first save"


def test_backup_disabled_with_backup_false(tmp_path: Path) -> None:
    """Test that backup=False disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save - should NOT create backup when disabled
    storage.save([Todo(id=1, text="second")])

    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "Backup should not be created when backup=False"


def test_backup_preserves_latest_previous_content(tmp_path: Path) -> None:
    """Test that each save updates backup to contain the previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Multiple saves - backup should always have the previous content
    storage.save([Todo(id=1, text="version 1")])
    storage.save([Todo(id=1, text="version 2")])
    storage.save([Todo(id=1, text="version 3")])

    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")

    # Backup should contain "version 2" (the content before last save)
    assert "version 2" in backup_content
    assert "version 3" not in backup_content
