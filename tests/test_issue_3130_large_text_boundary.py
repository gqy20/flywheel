"""Tests for issue #3130: text field boundary tests for large text.

This module tests that the Todo and TodoStorage can handle large text values
(1MB+) without errors, verifying that the storage layer's DoS protection
doesn't break legitimate use cases with large but reasonable text fields.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoLargeText:
    """Tests for Todo handling of large text fields."""

    def test_from_dict_accepts_large_text_1mb(self) -> None:
        """Test that Todo.from_dict can handle 1MB text without error."""
        large_text = "x" * (1024 * 1024)  # 1MB of text
        data = {"id": 1, "text": large_text}

        todo = Todo.from_dict(data)

        assert todo.id == 1
        assert len(todo.text) == 1024 * 1024
        assert todo.text == large_text

    def test_from_dict_accepts_large_text_5mb(self) -> None:
        """Test that Todo.from_dict can handle 5MB text without error."""
        large_text = "y" * (5 * 1024 * 1024)  # 5MB of text
        data = {"id": 2, "text": large_text}

        todo = Todo.from_dict(data)

        assert todo.id == 2
        assert len(todo.text) == 5 * 1024 * 1024


class TestStorageLargeText:
    """Tests for TodoStorage handling of large text fields."""

    def test_storage_save_load_large_text_roundtrip_1mb(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test that storage can save/load roundtrip 1MB text correctly."""
        db = tmp_path / "large_text.json"
        storage = TodoStorage(str(db))

        large_text = "a" * (1024 * 1024)  # 1MB
        todos = [Todo(id=1, text=large_text)]

        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        assert len(loaded[0].text) == 1024 * 1024
        assert loaded[0].text == large_text

    def test_storage_save_load_large_text_roundtrip_5mb(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test that storage can save/load roundtrip 5MB text correctly."""
        db = tmp_path / "large_text_5mb.json"
        storage = TodoStorage(str(db))

        large_text = "b" * (5 * 1024 * 1024)  # 5MB
        todos = [Todo(id=1, text=large_text)]

        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        assert len(loaded[0].text) == 5 * 1024 * 1024
        assert loaded[0].text == large_text


class TestTodoRenameLargeText:
    """Tests for Todo.rename with large text."""

    def test_rename_accepts_large_text(self) -> None:
        """Test that Todo.rename can handle large text."""
        todo = Todo(id=1, text="original")
        large_text = "z" * (1024 * 1024)  # 1MB

        todo.rename(large_text)

        assert len(todo.text) == 1024 * 1024
        assert todo.text == large_text
