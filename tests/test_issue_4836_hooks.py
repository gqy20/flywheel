"""Tests for issue #4836: File change callback hooks support.

This test suite verifies that TodoStorage supports optional callback hooks
for on_pre_save, on_post_save, and on_post_load to enable extensibility
without inheritance or wrapper patterns.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo

if TYPE_CHECKING:
    pass


class TestHooksSupport:
    """Test callback hooks in TodoStorage."""

    def test_no_hooks_behavior_unchanged(self, tmp_path: Path) -> None:
        """Verify that not passing callbacks preserves existing behavior."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Should work without any hooks
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_on_post_save_called_after_save(self, tmp_path: Path) -> None:
        """Verify on_post_save is called after save with the todos list."""
        db = tmp_path / "todo.json"
        called_with: list[Todo] | None = None

        def on_post_save(todos: list[Todo]) -> None:
            nonlocal called_with
            called_with = todos

        storage = TodoStorage(str(db), on_post_save=on_post_save)

        todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(todos)

        assert called_with is not None
        assert len(called_with) == 2
        assert called_with[0].text == "first"
        assert called_with[1].text == "second"

    def test_on_post_load_called_after_load(self, tmp_path: Path) -> None:
        """Verify on_post_load is called after load with the todos list."""
        db = tmp_path / "todo.json"
        called_with: list[Todo] | None = None

        def on_post_load(todos: list[Todo]) -> None:
            nonlocal called_with
            called_with = todos

        storage = TodoStorage(str(db), on_post_load=on_post_load)

        # First save some data
        todos = [Todo(id=1, text="saved")]
        storage.save(todos)

        # Reset tracker
        called_with = None

        # Load should trigger callback
        loaded = storage.load()

        assert called_with is not None
        assert len(called_with) == 1
        assert called_with[0].text == "saved"
        # loaded should match
        assert loaded == called_with

    def test_on_pre_save_called_before_save(self, tmp_path: Path) -> None:
        """Verify on_pre_save is called before save with the todos list."""
        db = tmp_path / "todo.json"
        pre_save_called = False

        def on_pre_save(todos: list[Todo]) -> None:
            nonlocal pre_save_called
            pre_save_called = True

        storage = TodoStorage(str(db), on_pre_save=on_pre_save)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        assert pre_save_called is True

    def test_all_hooks_together(self, tmp_path: Path) -> None:
        """Verify all three hooks work together."""
        db = tmp_path / "todo.json"
        calls: list[str] = []

        def on_pre_save(todos: list[Todo]) -> None:
            calls.append(f"pre_save:{len(todos)}")

        def on_post_save(todos: list[Todo]) -> None:
            calls.append(f"post_save:{len(todos)}")

        def on_post_load(todos: list[Todo]) -> None:
            calls.append(f"post_load:{len(todos)}")

        storage = TodoStorage(
            str(db),
            on_pre_save=on_pre_save,
            on_post_save=on_post_save,
            on_post_load=on_post_load,
        )

        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        storage.load()

        assert "pre_save:1" in calls
        assert "post_save:1" in calls
        assert "post_load:1" in calls
        # pre_save should come before post_save
        assert calls.index("pre_save:1") < calls.index("post_save:1")

    def test_hook_exception_propagates(self, tmp_path: Path) -> None:
        """Verify that hook exceptions propagate to caller."""
        db = tmp_path / "todo.json"

        def failing_hook(todos: list[Todo]) -> None:
            raise ValueError("Hook failed!")

        storage = TodoStorage(str(db), on_post_save=failing_hook)

        todos = [Todo(id=1, text="test")]
        with pytest.raises(ValueError, match="Hook failed!"):
            storage.save(todos)

    def test_on_post_load_not_called_on_empty_file(self, tmp_path: Path) -> None:
        """Verify on_post_load is still called when file doesn't exist (empty result)."""
        db = tmp_path / "todo.json"
        called = False

        def on_post_load(todos: list[Todo]) -> None:
            nonlocal called
            called = True

        storage = TodoStorage(str(db), on_post_load=on_post_load)

        # File doesn't exist, load returns []
        result = storage.load()

        # Hook should still be called with empty list
        assert called is True
        assert result == []
