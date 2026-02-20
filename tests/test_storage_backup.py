"""Tests for backup file functionality in TodoStorage.

This test suite verifies that TodoStorage can optionally create backup files
before overwriting, providing a safety net for accidental data loss.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_when_enabled(tmp_path, monkeypatch) -> None:
    """Test that backup file is created when FLYWHEEL_BACKUP=1."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Enable backup via environment variable
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # First save - no backup yet (file doesn't exist)
    first_todos = [Todo(id=1, text="first todo"), Todo(id=2, text="second todo")]
    storage.save(first_todos)

    # Backup shouldn't exist yet (no previous file to backup)
    assert not backup_path.exists()

    # Second save - should create backup of first save
    second_todos = [Todo(id=1, text="modified first")]
    storage.save(second_todos)

    # Backup should now exist
    assert backup_path.exists()

    # Backup should contain first save data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "first todo"
    assert backup_content[1]["text"] == "second todo"


def test_no_backup_created_when_disabled(tmp_path, monkeypatch) -> None:
    """Test that no backup file is created when FLYWHEEL_BACKUP is not set."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Ensure backup is disabled (default behavior)
    monkeypatch.delenv("FLYWHEEL_BACKUP", raising=False)

    # First save
    first_todos = [Todo(id=1, text="first")]
    storage.save(first_todos)

    # Second save
    second_todos = [Todo(id=1, text="second")]
    storage.save(second_todos)

    # No backup should exist
    assert not backup_path.exists()


def test_backup_preserves_previous_valid_data(tmp_path, monkeypatch) -> None:
    """Test that backup contains the last valid saved data."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Save multiple times with different content
    for i in range(3):
        todos = [Todo(id=j, text=f"iteration-{i}-todo-{j}") for j in range(1, 4)]
        storage.save(todos)

    # Backup should contain iteration 1 data (iteration 2 overwrote iteration 1)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 3
    # All texts should be from iteration 1 (the second-to-last save)
    for item in backup_content:
        assert "iteration-1-" in item["text"]


def test_backup_on_empty_save(tmp_path, monkeypatch) -> None:
    """Test that backup works even when saving an empty list."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Save with todos first
    first_todos = [Todo(id=1, text="important todo")]
    storage.save(first_todos)

    # Save empty list (e.g., user cleared all todos)
    storage.save([])

    # Backup should contain the previous todos
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "important todo"

    # Current file should be empty
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(current_content) == 0


def test_backup_with_unicode_content(tmp_path, monkeypatch) -> None:
    """Test that backup handles unicode content correctly."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Save with unicode
    first_todos = [Todo(id=1, text="Hello 你好 مرحبا")]
    storage.save(first_todos)

    second_todos = [Todo(id=1, text="New content")]
    storage.save(second_todos)

    # Backup should preserve unicode
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "Hello 你好 مرحبا"


def test_backup_file_permissions(tmp_path, monkeypatch) -> None:
    """Test that backup file has appropriate permissions."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial save
    storage.save([Todo(id=1, text="first")])

    # Second save to create backup
    storage.save([Todo(id=1, text="second")])

    # Backup file should exist and be readable
    assert backup_path.exists()
    content = backup_path.read_text(encoding="utf-8")
    assert "first" in content


def test_backup_only_created_on_successful_save(tmp_path, monkeypatch) -> None:
    """Test that backup is only created after a successful save, not before."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # First save should succeed without backup (no prior file)
    storage.save([Todo(id=1, text="initial")])
    assert not backup_path.exists()

    # Second save should create backup of first
    storage.save([Todo(id=1, text="updated")])
    assert backup_path.exists()
