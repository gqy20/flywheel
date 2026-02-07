"""Tests for the minimal Todo framework."""

from __future__ import annotations

from pathlib import Path

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


def test_storage_save_is_atomic(tmp_path, monkeypatch) -> None:
    """Test that save uses atomic temp file + rename pattern.

    This verifies data integrity: if the process crashes during write,
    the original file remains intact.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial state
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Track calls to replace (atomic rename on POSIX)
    replace_calls = []

    original_replace = Path.replace

    def capture_replace(self, target):
        replace_calls.append((self.name, target.name))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", capture_replace)

    # Save new data
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Verify atomic pattern: temp file was written then renamed to target
    assert len(replace_calls) == 1, "save should use exactly one atomic replace operation"
    temp_name, target_name = replace_calls[0]
    assert target_name == db.name, "temp file should be renamed to the target database file"
    assert temp_name.endswith(".tmp"), "temp file should use .tmp suffix"

    # Verify the final content was written correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"
