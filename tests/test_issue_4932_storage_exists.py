"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() provides a lightweight
way to check if the database file exists without loading or parsing it.

Issue: #4932
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_save(tmp_path) -> None:
    """Test that exists() returns False when database file does not exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Database file should not exist yet
    assert not db.exists()
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Database file should now exist
    assert db.exists()
    assert storage.exists() is True


def test_exists_does_not_raise_on_missing_file(tmp_path) -> None:
    """Test that exists() does not raise exception when file is missing."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should not raise, just return False
    result = storage.exists()
    assert result is False


def test_exists_does_not_read_file_contents(tmp_path, monkeypatch) -> None:
    """Test that exists() only checks path without reading file contents."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file
    todos = [Todo(id=1, text="secret data")]
    storage.save(todos)

    # Track if read_text was called
    original_read_text = Path.read_text
    read_text_called = []

    def tracking_read_text(self, *args, **kwargs):
        read_text_called.append(True)
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracking_read_text)

    # Call exists() - it should NOT read the file
    result = storage.exists()

    # Verify exists returned True without reading file
    assert result is True
    assert len(read_text_called) == 0, "exists() should not read file contents"
