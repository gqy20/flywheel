"""Tests for auto-backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup file
before overwriting existing data, allowing recovery from mistakes or corruption.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """Test that first save (when file doesn't exist) doesn't create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist yet
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Verify no backup file was created
    backup_file = tmp_path / "todo.json.bak"
    assert not backup_file.exists(), "Backup should not be created on first save"

    # Verify main file exists with correct content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_second_save_creates_backup(tmp_path) -> None:
    """Test that second save creates a backup of the previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Second save - should create backup
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_file = tmp_path / "todo.json.bak"
    assert backup_file.exists(), "Backup file should be created on second save"

    # Verify backup contains original content
    import json
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original"

    # Verify main file has new content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "updated"
    assert loaded[1].text == "new"


def test_backup_false_disables_backup(tmp_path) -> None:
    """Test that backup=False parameter disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Second save with backup=False
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=False)

    # Verify no backup file was created
    backup_file = tmp_path / "todo.json.bak"
    assert not backup_file.exists(), "Backup should not be created when backup=False"

    # Verify main file has new content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"


def test_backup_overwrites_previous_backup(tmp_path) -> None:
    """Test that each save overwrites the previous backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First, second, third saves
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=1, text="v2")])
    storage.save([Todo(id=1, text="v3")])

    # Backup should contain v2 (the previous version before v3)
    import json
    backup_file = tmp_path / "todo.json.bak"
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "v2"

    # Main file should have v3
    loaded = storage.load()
    assert loaded[0].text == "v3"
