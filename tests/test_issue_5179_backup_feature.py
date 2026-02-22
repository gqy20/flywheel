"""Tests for automatic backup before save feature (Issue #5179).

This test suite verifies that TodoStorage.save() supports optional backup
functionality to preserve existing files before overwriting.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_false_by_default_no_backup_created(tmp_path) -> None:
    """Test that backup=False (default) does not create a backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates the file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Second save with default (backup=False)
    todos2 = [Todo(id=1, text="updated")]
    storage.save(todos2)

    # Verify no backup file was created
    backup_path = Path(str(db) + ".bak")
    assert not backup_path.exists()


def test_backup_true_creates_backup_file(tmp_path) -> None:
    """Test that backup=True creates a .bak file with old content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates the file
    original_todos = [Todo(id=1, text="original content"), Todo(id=2, text="second item")]
    storage.save(original_todos)

    # Second save with backup=True
    new_todos = [Todo(id=1, text="new content")]
    storage.save(new_todos, backup=True)

    # Verify backup file was created
    backup_path = Path(str(db) + ".bak")
    assert backup_path.exists()

    # Verify backup contains original content
    backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_data) == 2
    assert backup_data[0]["text"] == "original content"
    assert backup_data[1]["text"] == "second item"


def test_backup_on_first_save_no_existing_file(tmp_path) -> None:
    """Test that backup=True on first save (no existing file) does not fail."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save with backup=True - no existing file to backup
    todos = [Todo(id=1, text="first save")]
    storage.save(todos, backup=True)

    # File should exist with new content
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "first save"

    # No backup file should exist since there was nothing to backup
    backup_path = Path(str(db) + ".bak")
    assert not backup_path.exists()


def test_backup_preserves_file_permissions(tmp_path) -> None:
    """Test that backup file has the same permissions as the original file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Get original file permissions
    original_mode = db.stat().st_mode

    # Save with backup
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=True)

    # Verify backup has same permissions
    backup_path = Path(str(db) + ".bak")
    backup_mode = backup_path.stat().st_mode
    assert backup_mode == original_mode


def test_backup_overwrites_existing_backup(tmp_path) -> None:
    """Test that successive saves with backup overwrite the previous backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save with backup
    storage.save([Todo(id=1, text="version 2")], backup=True)

    # Third save with backup
    storage.save([Todo(id=1, text="version 3")], backup=True)

    # Backup should contain version 2, not version 1
    backup_path = Path(str(db) + ".bak")
    backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_data[0]["text"] == "version 2"
