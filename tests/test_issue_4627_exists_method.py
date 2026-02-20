"""Tests for the exists() method in TodoStorage.

This test suite verifies the exists() method added in issue #4627,
which provides an efficient way to check if storage file exists
without parsing JSON.

Acceptance criteria:
- exists() method returns bool type
- Return value is equivalent to Path.exists() result
- Method has docstring documentation
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestExistsMethod:
    """Tests for TodoStorage.exists() method."""

    def test_exists_returns_false_when_file_does_not_exist(self, tmp_path: Path) -> None:
        """Test that exists() returns False when storage file does not exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        assert storage.exists() is False

    def test_exists_returns_true_when_file_exists(self, tmp_path: Path) -> None:
        """Test that exists() returns True when storage file exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a valid storage file
        storage.save([Todo(id=1, text="test")])

        assert storage.exists() is True

    def test_exists_returns_false_for_nonexistent_default_path(self, tmp_path: Path, monkeypatch) -> None:
        """Test that exists() returns False when using default path in empty directory."""
        # Change to tmp_path where .todo.json doesn't exist
        monkeypatch.chdir(tmp_path)
        storage = TodoStorage()  # Uses default .todo.json

        assert storage.exists() is False

    def test_exists_returns_bool_type(self, tmp_path: Path) -> None:
        """Test that exists() returns a bool type (not truthy value)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        result = storage.exists()
        assert isinstance(result, bool)

    def test_exists_after_save_and_delete(self, tmp_path: Path) -> None:
        """Test that exists() correctly reflects file state after save and delete."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Initially doesn't exist
        assert storage.exists() is False

        # After save, exists
        storage.save([Todo(id=1, text="test")])
        assert storage.exists() is True

        # After delete, doesn't exist
        db.unlink()
        assert storage.exists() is False
