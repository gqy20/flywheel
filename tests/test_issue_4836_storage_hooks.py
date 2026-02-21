"""Tests for storage hooks (callbacks) feature.

Issue #4836: Add file change callback hooks support.

This test suite verifies that TodoStorage supports optional hooks:
- on_pre_save: called before save
- on_post_save: called after save
- on_post_load: called after load
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from flywheel.storage import TodoStorage
from flywheel.todo import Todo

if TYPE_CHECKING:
    pass


def test_no_hooks_behavior_unchanged(tmp_path: Path) -> None:
    """Verify that not passing hooks leaves behavior unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test"), Todo(id=2, text="another")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "test"
    assert loaded[1].text == "another"


def test_on_post_save_called_after_save(tmp_path: Path) -> None:
    """Verify on_post_save is called after save with correct data."""
    db = tmp_path / "todo.json"

    saved_todos = []

    def capture_save(todos: list[Todo]) -> None:
        saved_todos.extend(todos)

    storage = TodoStorage(str(db), on_post_save=capture_save)

    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    storage.save(todos)

    assert len(saved_todos) == 2
    assert saved_todos[0].text == "first"
    assert saved_todos[1].text == "second"


def test_on_post_load_called_after_load(tmp_path: Path) -> None:
    """Verify on_post_load is called after load with correct data."""
    db = tmp_path / "todo.json"

    loaded_todos = []

    def capture_load(todos: list[Todo]) -> None:
        loaded_todos.extend(todos)

    storage = TodoStorage(str(db), on_post_load=capture_load)

    # First save some data
    todos = [Todo(id=1, text="loaded test")]
    storage.save(todos)

    # Clear and load
    loaded_todos.clear()
    result = storage.load()

    assert len(loaded_todos) == 1
    assert loaded_todos[0].text == "loaded test"
    assert result == loaded_todos


def test_on_pre_save_called_before_save(tmp_path: Path) -> None:
    """Verify on_pre_save is called before save with correct data."""
    db = tmp_path / "todo.json"

    pre_save_todos = []
    call_order = []

    def capture_pre_save(todos: list[Todo]) -> None:
        pre_save_todos.extend(todos)
        call_order.append("pre_save")

    def capture_post_save(todos: list[Todo]) -> None:
        call_order.append("post_save")

    storage = TodoStorage(
        str(db),
        on_pre_save=capture_pre_save,
        on_post_save=capture_post_save,
    )

    todos = [Todo(id=1, text="pre save test")]
    storage.save(todos)

    assert len(pre_save_todos) == 1
    assert pre_save_todos[0].text == "pre save test"
    # Verify pre_save is called before post_save
    assert call_order == ["pre_save", "post_save"]


def test_hook_receives_copy_of_todos(tmp_path: Path) -> None:
    """Verify hooks receive the todos list (may be same or copy)."""
    db = tmp_path / "todo.json"

    received_todos = None

    def capture(todos: list[Todo]) -> None:
        nonlocal received_todos
        received_todos = todos

    storage = TodoStorage(str(db), on_post_save=capture)

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert received_todos is not None
    assert len(received_todos) == 1


def test_hooks_work_with_empty_todos_list(tmp_path: Path) -> None:
    """Verify hooks work correctly with empty todos list."""
    db = tmp_path / "todo.json"

    save_called_with = None
    load_called_with = None

    def capture_save(todos: list[Todo]) -> None:
        nonlocal save_called_with
        save_called_with = list(todos)

    def capture_load(todos: list[Todo]) -> None:
        nonlocal load_called_with
        load_called_with = list(todos)

    storage = TodoStorage(
        str(db),
        on_post_save=capture_save,
        on_post_load=capture_load,
    )

    # Save empty list
    storage.save([])
    assert save_called_with == []

    # Load empty list
    load_called_with = None
    storage.load()
    assert load_called_with == []


def test_multiple_saves_trigger_hooks_each_time(tmp_path: Path) -> None:
    """Verify hooks are triggered on each save operation."""
    db = tmp_path / "todo.json"

    call_count = 0

    def count_save(todos: list[Todo]) -> None:
        nonlocal call_count
        call_count += 1

    storage = TodoStorage(str(db), on_post_save=count_save)

    storage.save([Todo(id=1, text="first")])
    assert call_count == 1

    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
    assert call_count == 2

    storage.save([])
    assert call_count == 3


def test_hooks_accept_none_gracefully(tmp_path: Path) -> None:
    """Verify passing None for hooks works (same as not passing)."""
    db = tmp_path / "todo.json"

    storage = TodoStorage(
        str(db),
        on_pre_save=None,
        on_post_save=None,
        on_post_load=None,
    )

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
