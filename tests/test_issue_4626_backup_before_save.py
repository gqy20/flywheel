"""Tests for backup functionality before save.

Issue #4626: Add backup functionality to automatically backup existing data
before save overwrites it.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """Test that saving for the first time does not create a backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Verify the file was created
    assert db.exists()

    # Verify NO backup file was created (since there was no existing file)
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists()


def test_save_over_existing_file_creates_backup(tmp_path) -> None:
    """Test that saving over an existing file creates a .bak backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original todo"), Todo(id=2, text="second")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Save new data (overwriting existing)
    new_todos = [Todo(id=1, text="new todo")]
    storage.save(new_todos)

    # Verify the backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Verify backup contains the original content
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content

    # Verify the main file has the new content
    new_content = db.read_text(encoding="utf-8")
    parsed = json.loads(new_content)
    assert len(parsed) == 1
    assert parsed[0]["text"] == "new todo"


def test_backup_content_matches_original(tmp_path) -> None:
    """Test that backup content exactly matches the file before overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data with various fields
    original_todos = [
        Todo(id=1, text="task one", done=False),
        Todo(id=2, text="task two", done=True),
        Todo(id=3, text="task with unicode: 你好世界"),
    ]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Save new data
    new_todos = [Todo(id=1, text="replacement")]
    storage.save(new_todos)

    # Verify backup content matches original
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content

    # Parse and verify the backup data
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 3
    assert backup_data[0]["text"] == "task one"
    assert backup_data[0]["done"] is False
    assert backup_data[1]["text"] == "task two"
    assert backup_data[1]["done"] is True
    assert backup_data[2]["text"] == "task with unicode: 你好世界"


def test_backup_replaced_on_second_overwrite(tmp_path) -> None:
    """Test that multiple overwrites update the backup each time."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    first_todos = [Todo(id=1, text="first")]
    storage.save(first_todos)

    # Second save - creates backup of first
    second_todos = [Todo(id=1, text="second")]
    storage.save(second_todos)

    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert json.loads(backup_content)[0]["text"] == "first"

    # Third save - backup should now contain second (not first)
    third_todos = [Todo(id=1, text="third")]
    storage.save(third_todos)

    backup_content = backup_path.read_text(encoding="utf-8")
    assert json.loads(backup_content)[0]["text"] == "second"

    # Main file should have third
    main_content = db.read_text(encoding="utf-8")
    assert json.loads(main_content)[0]["text"] == "third"
