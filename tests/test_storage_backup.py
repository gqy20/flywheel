"""Tests for auto-backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() creates .bak backup files
before overwriting existing data, enabling recovery from mistakes or corruption.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """Test that first save (file doesn't exist) does not create backup."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist yet
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Verify file was created but backup was not
    assert db.exists()
    assert not backup.exists()


def test_second_save_creates_backup(tmp_path) -> None:
    """Test that second save (file exists) creates .bak backup."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    original_todos = [Todo(id=1, text="original content")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Second save - should create backup
    new_todos = [Todo(id=1, text="modified content"), Todo(id=2, text="new todo")]
    storage.save(new_todos)

    # Verify backup was created with original content
    assert backup.exists(), "Backup file should be created on second save"
    assert backup.read_text(encoding="utf-8") == original_content

    # Verify main file has new content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "modified content"
    assert loaded[1].text == "new todo"


def test_backup_parameter_false_disables_backup(tmp_path) -> None:
    """Test that backup=False disables backup creation."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Second save with backup=False
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos, backup=False)

    # Verify no backup was created
    assert not backup.exists()


def test_multiple_saves_update_backup(tmp_path) -> None:
    """Test that each subsequent save updates the backup."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="v1")])
    assert not backup.exists()

    # Second save - backup should be v1
    storage.save([Todo(id=1, text="v2")])
    assert "v1" in backup.read_text(encoding="utf-8")

    # Third save - backup should be v2
    storage.save([Todo(id=1, text="v3")])
    assert "v2" in backup.read_text(encoding="utf-8")
    assert "v1" not in backup.read_text(encoding="utf-8")
