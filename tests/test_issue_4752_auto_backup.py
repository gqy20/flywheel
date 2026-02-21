"""Tests for automatic backup feature (issue #4752).

This test suite verifies that TodoStorage.save() creates a .bak backup file
before overwriting existing data, enabling recovery from accidental operations
or data corruption.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that first save (when no file exists) does not create a backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Verify main file exists
    assert db.exists()

    # Verify no backup file was created on first save
    backup_file = tmp_path / "todo.json.bak"
    assert not backup_file.exists()


def test_second_save_creates_backup(tmp_path: Path) -> None:
    """Test that second save creates .bak backup with previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    first_todos = [Todo(id=1, text="first version")]
    storage.save(first_todos)

    # Second save
    second_todos = [Todo(id=1, text="second version"), Todo(id=2, text="new item")]
    storage.save(second_todos)

    # Verify backup file was created
    backup_file = tmp_path / "todo.json.bak"
    assert backup_file.exists()

    # Verify backup contains the first version content
    backup_storage = TodoStorage(str(backup_file))
    backup_todos = backup_storage.load()

    assert len(backup_todos) == 1
    assert backup_todos[0].text == "first version"


def test_backup_disabled_with_parameter(tmp_path: Path) -> None:
    """Test that backup=False parameter disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    first_todos = [Todo(id=1, text="first version")]
    storage.save(first_todos)

    # Second save with backup disabled
    second_todos = [Todo(id=1, text="second version")]
    storage.save(second_todos, backup=False)

    # Verify no backup file was created
    backup_file = tmp_path / "todo.json.bak"
    assert not backup_file.exists()


def test_backup_overwrites_previous_backup(tmp_path: Path) -> None:
    """Test that multiple saves update the backup to the previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save
    storage.save([Todo(id=1, text="version 2")])

    # Third save
    storage.save([Todo(id=1, text="version 3")])

    # Verify backup contains version 2 (previous to current)
    backup_file = tmp_path / "todo.json.bak"
    backup_storage = TodoStorage(str(backup_file))
    backup_todos = backup_storage.load()

    assert len(backup_todos) == 1
    assert backup_todos[0].text == "version 2"


def test_backup_preserves_unicode_content(tmp_path: Path) -> None:
    """Test that backup preserves unicode content correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save with unicode content
    unicode_todos = [Todo(id=1, text="unicode: 你好世界 🌍")]
    storage.save(unicode_todos)

    # Second save
    storage.save([Todo(id=1, text="new content")])

    # Verify backup preserves unicode
    backup_file = tmp_path / "todo.json.bak"
    backup_storage = TodoStorage(str(backup_file))
    backup_todos = backup_storage.load()

    assert backup_todos[0].text == "unicode: 你好世界 🌍"
