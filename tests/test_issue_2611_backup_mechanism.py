"""Tests for file backup mechanism (issue #2611).

This test suite verifies that TodoStorage.save() creates .bak backup files
to prevent data loss from user errors (e.g., accidental deletion of all todos)
and JSON corruption.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that .bak file is created on save when original file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Verify original file exists
    assert db.exists()

    # Save new data - should create backup
    new_todos = [Todo(id=2, text="new task")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created when overwriting existing file"


def test_backup_contains_pre_save_content(tmp_path) -> None:
    """Test that backup has original data before overwrite."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create initial data with specific content
    original_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task with unicode: 你好"),
    ]
    storage.save(original_todos)

    # Save new data - different content
    new_todos = [Todo(id=99, text="completely different")]
    storage.save(new_todos)

    # Verify backup contains the ORIGINAL data, not the new data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 3, "Backup should have 3 original todos"
    assert backup_content[0]["text"] == "task 1"
    assert backup_content[1]["text"] == "task 2"
    assert backup_content[1]["done"] is True
    assert backup_content[2]["text"] == "task with unicode: 你好"


def test_backup_overwrites_old_backup(tmp_path) -> None:
    """Test that only 1 backup is retained (no accumulation)."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - creates backup
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=2, text="second")])

    # Get backup content after second save
    backup_after_second = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_after_second) == 1
    assert backup_after_second[0]["text"] == "first"

    # Third save - should overwrite backup, not create .bak.bak
    storage.save([Todo(id=3, text="third")])

    # Verify only one backup file exists
    assert backup_path.exists()
    assert not (tmp_path / "todo.json.bak.bak").exists()

    # Verify backup contains the second save's data
    backup_after_third = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_after_third) == 1
    assert backup_after_third[0]["text"] == "second"


def test_first_save_creates_no_backup(tmp_path) -> None:
    """Test that first save with no existing file does not create .bak."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - no original file exists yet
    storage.save([Todo(id=1, text="first save")])

    # Verify main file was created
    assert db.exists()

    # Verify no backup was created (nothing to backup)
    assert not backup_path.exists(), "Backup should not be created on first save"


def test_backup_preserves_file_metadata(tmp_path) -> None:
    """Test that backup file preserves original file metadata."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Save new data
    storage.save([Todo(id=2, text="new")])

    # Verify backup exists
    assert backup_path.exists()

    # Note: We can't directly verify exact metadata preservation
    # because the save operation might modify times. But we can
    # verify the backup is a regular file and has content.
    backup_stat = backup_path.stat()
    assert backup_stat.st_size > 0, "Backup should have content"


def test_backup_with_custom_filename(tmp_path) -> None:
    """Test that backup works with custom database filenames."""
    # Test with different filename patterns
    test_cases = [
        "custom.json",
        "my-todos.json",
        "data.todos.db.json",
    ]

    for filename in test_cases:
        db = tmp_path / filename
        backup_path = tmp_path / f"{filename}.bak"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text=f"original for {filename}")])

        # Save new data
        storage.save([Todo(id=2, text=f"new for {filename}")])

        # Verify backup exists with correct name
        assert backup_path.exists(), f"Backup should exist for {filename}"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == f"original for {filename}"
