"""Tests for backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() can optionally create
a backup of the previous file before overwriting.

Issue: #5073 - Add data backup functionality
"""

from __future__ import annotations

import os
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_with_backup_creates_bak_file(tmp_path: Path) -> None:
    """Test that save(backup=True) creates a .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    initial_todos = [Todo(id=1, text="initial task")]
    storage.save(initial_todos)

    # Verify no backup exists yet
    bak_path = tmp_path / ".todo.json.bak"
    assert not bak_path.exists(), "Backup file should not exist initially"

    # Save new data with backup=True
    new_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
    storage.save(new_todos, backup=True)

    # Verify backup file was created
    assert bak_path.exists(), "Backup file should be created when backup=True"


def test_backup_contains_previous_content(tmp_path: Path) -> None:
    """Test that backup file contains the content before overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    initial_todos = [Todo(id=1, text="initial task"), Todo(id=2, text="second task")]
    storage.save(initial_todos)

    # Get initial content
    initial_content = db.read_text(encoding="utf-8")

    # Save new data with backup=True
    new_todos = [Todo(id=1, text="completely different")]
    storage.save(new_todos, backup=True)

    # Verify backup file contains the previous content
    bak_path = tmp_path / ".todo.json.bak"
    assert bak_path.exists(), "Backup file should exist"
    backup_content = bak_path.read_text(encoding="utf-8")
    assert backup_content == initial_content, "Backup should contain the previous file content"


def test_backup_file_has_same_permissions(tmp_path: Path) -> None:
    """Test that backup file has same permissions as main file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    initial_todos = [Todo(id=1, text="task")]
    storage.save(initial_todos)

    # Save with backup
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=True)

    # Check permissions match
    bak_path = tmp_path / ".todo.json.bak"
    main_stat = os.stat(db)
    bak_stat = os.stat(bak_path)

    # Compare permission bits (mode & 0o777)
    assert main_stat.st_mode & 0o777 == bak_stat.st_mode & 0o777, (
        "Backup file should have same permissions as main file"
    )


def test_save_without_backup_does_not_create_bak_file(tmp_path: Path) -> None:
    """Test that save(backup=False) does not create a backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    initial_todos = [Todo(id=1, text="initial task")]
    storage.save(initial_todos)

    bak_path = tmp_path / ".todo.json.bak"

    # Save without backup (default)
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=False)

    # Verify no backup created
    assert not bak_path.exists(), "No backup file should be created when backup=False"

    # Also test default behavior (no backup arg)
    storage.save(initial_todos)
    assert not bak_path.exists(), "No backup file should be created by default"


def test_multiple_saves_with_backup_overwrites_previous_backup(tmp_path: Path) -> None:
    """Test that multiple saves with backup overwrite the previous backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    bak_path = tmp_path / ".todo.json.bak"

    # First save (no previous file, so no backup created even with backup=True)
    first_todos = [Todo(id=1, text="first")]
    storage.save(first_todos, backup=True)
    # No backup should exist since there was no previous file
    assert not bak_path.exists(), "No backup when no previous file existed"

    # Second save with backup
    second_todos = [Todo(id=1, text="second")]
    storage.save(second_todos, backup=True)
    assert bak_path.exists(), "Backup should exist after second save"
    backup_content = bak_path.read_text(encoding="utf-8")
    assert "first" in backup_content, "Backup should contain first save"

    # Third save with backup
    third_todos = [Todo(id=1, text="third")]
    storage.save(third_todos, backup=True)
    backup_content = bak_path.read_text(encoding="utf-8")
    assert "second" in backup_content, "Backup should contain second save (overwritten)"
    assert "first" not in backup_content, "First backup should be overwritten"
