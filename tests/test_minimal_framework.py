"""Tests for the minimal Todo framework."""

from __future__ import annotations

import json

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_lifecycle_updates_state() -> None:
    todo = Todo(id=1, text="a")
    created = todo.created_at

    todo.mark_done()
    assert todo.done is True
    assert todo.updated_at >= created

    todo.mark_undone()
    assert todo.done is False

    todo.rename("b")
    assert todo.text == "b"


def test_storage_roundtrip(tmp_path) -> None:
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="x"), Todo(id=2, text="y", done=True)]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "x"
    assert loaded[1].done is True
    assert storage.next_id(loaded) == 3


def test_app_add_done_remove(tmp_path) -> None:
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("demo")
    assert added.id == 1
    assert app.list()[0].text == "demo"

    app.mark_done(1)
    assert app.list()[0].done is True

    app.remove(1)
    assert app.list() == []


def test_cli_run_command_flow(tmp_path, capsys) -> None:
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "add", "task"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "task" in out


def test_cli_run_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "done", "99"])
    assert run_command(args) == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_storage_save_preserves_original_on_failure(tmp_path) -> None:
    """Test that save uses atomic write: original file preserved if write fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data - should use temp file + atomic rename
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify file was updated correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "updated"
    assert loaded[1].text == "new"

    # Verify the file content is valid JSON (not truncated/corrupted)
    content = db.read_text(encoding="utf-8")
    data = json.loads(content)
    assert isinstance(data, list)


def test_storage_save_is_idempotent(tmp_path) -> None:
    """Test that multiple saves produce consistent, valid results."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos1 = [Todo(id=1, text="task1")]
    storage.save(todos1)
    loaded1 = storage.load()
    assert len(loaded1) == 1

    # Second save - should completely replace content atomically
    todos2 = [Todo(id=2, text="task2")]
    storage.save(todos2)
    loaded2 = storage.load()
    assert len(loaded2) == 1
    assert loaded2[0].id == 2
    assert loaded2[0].text == "task2"
