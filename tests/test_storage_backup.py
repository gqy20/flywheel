"""Tests for automatic backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
before saving, preventing data loss from accidental deletions or corruption.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save creates a .bak file when previous file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="modified task")]
    storage.save(new_todos)

    # Verify backup exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_save_does_not_create_backup_on_first_save(tmp_path) -> None:
    """Test that save does not create backup when no previous file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no previous file should exist
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Verify no backup was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_save_rotates_backups_with_limit(tmp_path) -> None:
    """Test that backups rotate with configurable limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=3)

    # Create multiple saves to test rotation
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # Check backup files exist
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Should have limited backups (check we can read at least one)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] in ["version 0", "version 1", "version 2", "version 3"]


def test_backup_default_limit_is_3(tmp_path) -> None:
    """Test that default backup limit is 3."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Check default limit
    assert storage.backup_limit == 3


def test_backup_with_zero_limit_disables_backups(tmp_path) -> None:
    """Test that backup_limit=0 disables backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=0)

    # Create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data - should NOT create backup when limit is 0
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Verify no backup was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created when backup_limit=0"


def test_backup_content_matches_previous_state(tmp_path) -> None:
    """Test that backup exactly matches the previous file state."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific content
    original_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
    ]
    storage.save(original_todos)

    # Get the original file content for comparison
    original_content = db.read_text(encoding="utf-8")

    # Save new data
    new_todos = [Todo(id=3, text="new task")]
    storage.save(new_todos)

    # Verify backup matches original
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should exactly match previous state"
