"""Tests for issue #4836: File change callback hooks support.

This test suite verifies that TodoStorage supports optional callback hooks
for pre_save, post_save, and post_load operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo

if TYPE_CHECKING:
    pass


class TestStorageHooks:
    """Tests for storage callback hooks."""

    def test_no_hooks_behavior_unchanged(self, tmp_path: Path) -> None:
        """Verify that not passing hooks leaves behavior unchanged."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_on_post_save_called_after_save(self, tmp_path: Path) -> None:
        """Verify on_post_save is called after save with correct data."""
        db = tmp_path / "todo.json"
        captured_todos: list[Todo] = []

        def on_post_save(todos: list[Todo]) -> None:
            captured_todos.extend(todos)

        storage = TodoStorage(str(db), on_post_save=on_post_save)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        assert len(captured_todos) == 1
        assert captured_todos[0].text == "test todo"

    def test_on_post_load_called_after_load(self, tmp_path: Path) -> None:
        """Verify on_post_load is called after load with correct data."""
        db = tmp_path / "todo.json"
        captured_todos: list[Todo] = []

        def on_post_load(todos: list[Todo]) -> None:
            captured_todos.extend(todos)

        storage = TodoStorage(str(db), on_post_load=on_post_load)

        # First save some data
        todos = [Todo(id=1, text="saved todo"), Todo(id=2, text="another")]
        storage.save(todos)

        # Now load - callback should be invoked
        loaded = storage.load()

        assert len(captured_todos) == 2
        assert captured_todos[0].text == "saved todo"
        assert captured_todos[1].text == "another"
        assert len(loaded) == 2  # Original return still works

    def test_on_pre_save_called_before_save(self, tmp_path: Path) -> None:
        """Verify on_pre_save is called before save with correct data."""
        db = tmp_path / "todo.json"
        captured_todos: list[Todo] = []
        save_count = 0

        def on_pre_save(todos: list[Todo]) -> list[Todo]:
            captured_todos.extend(todos)
            nonlocal save_count
            save_count += 1
            return todos

        storage = TodoStorage(str(db), on_pre_save=on_pre_save)

        todos = [Todo(id=1, text="pre-save test")]
        storage.save(todos)

        assert len(captured_todos) == 1
        assert captured_todos[0].text == "pre-save test"
        assert save_count == 1

    def test_pre_save_can_modify_todos(self, tmp_path: Path) -> None:
        """Verify pre_save hook can modify todos before saving."""
        db = tmp_path / "todo.json"

        def add_prefix(todos: list[Todo]) -> list[Todo]:
            for todo in todos:
                todo.text = f"[PREFIX] {todo.text}"
            return todos

        storage = TodoStorage(str(db), on_pre_save=add_prefix)

        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # Load and verify modification was persisted
        loaded = storage.load()
        assert loaded[0].text == "[PREFIX] original"

    def test_hook_exception_propagates(self, tmp_path: Path) -> None:
        """Verify hook exceptions are not silently swallowed."""
        db = tmp_path / "todo.json"

        def failing_hook(todos: list[Todo]) -> None:
            raise ValueError("Hook error")

        storage = TodoStorage(str(db), on_post_save=failing_hook)

        todos = [Todo(id=1, text="test")]
        with pytest.raises(ValueError, match="Hook error"):
            storage.save(todos)

    def test_multiple_hooks_work_together(self, tmp_path: Path) -> None:
        """Verify multiple hooks can be used together."""
        db = tmp_path / "todo.json"
        call_order: list[str] = []

        def pre_save(todos: list[Todo]) -> list[Todo]:
            call_order.append("pre_save")
            return todos

        def post_save(todos: list[Todo]) -> None:
            call_order.append("post_save")

        def post_load(todos: list[Todo]) -> None:
            call_order.append("post_load")

        storage = TodoStorage(
            str(db),
            on_pre_save=pre_save,
            on_post_save=post_save,
            on_post_load=post_load,
        )

        todos = [Todo(id=1, text="multi-hook test")]
        storage.save(todos)

        # pre_save should be called before post_save
        assert call_order == ["pre_save", "post_save"]

        # Now test load
        call_order.clear()
        storage.load()
        assert call_order == ["post_load"]

    def test_post_save_not_called_on_save_failure(self, tmp_path: Path) -> None:
        """Verify post_save is not called if save fails."""
        db = tmp_path / "todo.json"
        save_called = False

        def on_post_save(todos: list[Todo]) -> None:
            nonlocal save_called
            save_called = True

        # Make the parent directory a file to cause save to fail
        db.touch()  # Create file
        db_dir = db / "subdir" / "nested.json"
        storage_fail = TodoStorage(str(db_dir), on_post_save=on_post_save)

        todos = [Todo(id=1, text="test")]
        with pytest.raises(ValueError):  # Parent is a file, not directory
            storage_fail.save(todos)

        assert not save_called, "post_save should not be called on failure"
