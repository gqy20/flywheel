"""Tests for automatic backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() automatically creates
a backup of the existing file before overwriting it.

Issue: #4961
Feature: Automatic backup before save
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path: Path) -> None:
    """Test that save() creates a backup file when overwriting existing data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Get original content for comparison
    original_content = db.read_text(encoding="utf-8")

    # Save new data (should create backup)
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = tmp_path / ".todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original content
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should contain original data"

    # Verify backup has correct parsed content
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 2
    assert backup_data[0]["text"] == "original task"
    assert backup_data[1]["text"] == "another task"


def test_save_with_backup_false_skips_backup(tmp_path: Path) -> None:
    """Test that save(backup=False) does not create a backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Delete any existing backup
    backup_path = tmp_path / ".todo.json.bak"
    if backup_path.exists():
        backup_path.unlink()

    # Save with backup=False
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos, backup=False)

    # Verify no backup file was created
    assert not backup_path.exists(), "No backup file should be created when backup=False"


def test_consecutive_saves_update_backup(tmp_path: Path) -> None:
    """Test that consecutive saves update the backup to the previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    backup_path = tmp_path / ".todo.json.bak"

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)
    v1_content = db.read_text(encoding="utf-8")

    # Second save
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)
    v2_content = db.read_text(encoding="utf-8")

    # Third save
    todos_v3 = [Todo(id=1, text="version 3")]
    storage.save(todos_v3)

    # Verify backup contains v2 content (previous version)
    assert backup_path.exists()
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == v2_content

    # Verify current file has v3 content
    current_content = db.read_text(encoding="utf-8")
    assert current_content != v1_content
    assert current_content != v2_content


def test_backup_failure_does_not_prevent_save(tmp_path: Path) -> None:
    """Test that if backup fails, the save operation still completes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Create a read-only backup path that will cause backup to fail
    backup_path = tmp_path / ".todo.json.bak"
    backup_path.mkdir(mode=0o500)  # Create as directory to make backup fail

    try:
        # Save should still succeed even if backup fails
        new_todos = [Todo(id=1, text="new")]
        storage.save(new_todos)

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "new"
    finally:
        # Cleanup: restore permissions for tmp_path cleanup
        import os

        os.chmod(backup_path, 0o755)
        backup_path.rmdir()


def test_no_backup_created_when_file_does_not_exist(tmp_path: Path) -> None:
    """Test that no backup is created when saving to a new file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    backup_path = tmp_path / ".todo.json.bak"

    # Save to new file (no existing file to backup)
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # No backup should exist
    assert not backup_path.exists(), "No backup should be created for new file"
