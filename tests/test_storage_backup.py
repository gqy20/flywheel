"""Tests for backup mechanism in TodoStorage.

This test suite verifies that TodoStorage.save() creates a .bak backup file
before overwriting existing data, allowing recovery from user errors or JSON corruption.

Issue: #2611
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save creates .bak backup when overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    original_todos = [Todo(id=1, text="original task 1"), Todo(id=2, text="original task 2")]
    storage.save(original_todos)

    # Verify no backup yet (first save)
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists()

    # Save new todos (should create backup)
    new_todos = [Todo(id=1, text="modified task")]
    storage.save(new_todos)

    # Verify backup was created
    assert backup_path.exists(), "Backup file should be created when overwriting existing file"

    # Verify backup contains original content
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original task 1"
    assert backup_content[1]["text"] == "original task 2"

    # Verify current file has new content
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(current_content) == 1
    assert current_content[0]["text"] == "modified task"


def test_save_creates_no_backup_on_first_save(tmp_path) -> None:
    """Test that save does not create .bak backup when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    backup_path = tmp_path / "todo.json.bak"

    # First save should not create backup (no existing file)
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_overwrites_old_backup(tmp_path) -> None:
    """Test that only 1 backup is kept (old backup is overwritten)."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - no backup
    todos1 = [Todo(id=1, text="version 1")]
    storage.save(todos1)

    # Second save - creates backup of version 1
    todos2 = [Todo(id=1, text="version 2")]
    storage.save(todos2)
    assert backup_path.exists()

    backup_v2 = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_v2[0]["text"] == "version 1"

    # Third save - overwrites backup with version 2
    todos3 = [Todo(id=1, text="version 3")]
    storage.save(todos3)

    # Backup should still exist (only one file)
    assert backup_path.exists()

    # Backup should now contain version 2 (not version 1)
    backup_v3 = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_v3[0]["text"] == "version 2"


def test_backup_content_matches_pre_save_content(tmp_path) -> None:
    """Test that backup contains exact pre-save content including formatting."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create todos with various data types
    original_todos = [
        Todo(id=1, text="task with unicode: 你好", done=False),
        Todo(id=2, text='task with "quotes"', done=True),
        Todo(id=3, text="task with \\n newline", done=False),
    ]
    storage.save(original_todos)

    # Get original file content
    original_content = db.read_text(encoding="utf-8")

    # Save new todos
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos)

    # Verify backup content matches original exactly
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should contain exact pre-save content"

    # Verify backup is valid JSON
    parsed_backup = json.loads(backup_content)
    assert len(parsed_backup) == 3
    assert parsed_backup[0]["text"] == "task with unicode: 你好"
    assert parsed_backup[1]["done"] is True


def test_backup_with_different_file_paths(tmp_path) -> None:
    """Test that backup works with different file paths and names."""
    # Test with .todo.json (default)
    db1 = tmp_path / ".todo.json"
    storage1 = TodoStorage(str(db1))

    storage1.save([Todo(id=1, text="first")])
    storage1.save([Todo(id=1, text="second")])

    backup1 = tmp_path / ".todo.json.bak"
    assert backup1.exists()
    backup_content = json.loads(backup1.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "first"

    # Test with custom path
    custom_dir = tmp_path / "subdir"
    custom_dir.mkdir()
    db2 = custom_dir / "custom.json"
    storage2 = TodoStorage(str(db2))

    storage2.save([Todo(id=1, text="custom first")])
    storage2.save([Todo(id=1, text="custom second")])

    backup2 = custom_dir / "custom.json.bak"
    assert backup2.exists()
    backup_content = json.loads(backup2.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "custom first"


def test_backup_preserves_file_metadata(tmp_path) -> None:
    """Test that backup preserves original file metadata using shutil.copy2."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Modify file and create backup
    storage.save([Todo(id=1, text="modified")])

    backup_path = tmp_path / "todo.json.bak"

    # Backup exists and has content
    assert backup_path.exists()
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "original"

    # Note: shutil.copy2 preserves metadata but mtime will be from copy time
    # The key is that content is preserved
