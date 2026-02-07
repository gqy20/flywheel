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


def test_storage_rejects_path_traversal_with_parent_dir_sequences() -> None:
    """Path traversal via '../' sequences should be rejected."""
    import pytest
    with pytest.raises(ValueError, match="parent directory"):
        TodoStorage("../../../etc/passwd")


def test_storage_rejects_parent_dir_at_start() -> None:
    """Paths starting with '..' should be rejected."""
    import pytest
    with pytest.raises(ValueError, match="parent directory"):
        TodoStorage("../etc/passwd")


def test_storage_rejects_parent_dir_in_middle() -> None:
    """Paths with '../' in the middle should be rejected."""
    import pytest
    with pytest.raises(ValueError, match="parent directory"):
        TodoStorage("subdir/../../../etc/passwd")


def test_storage_rejects_backslash_parent_dir_sequences() -> None:
    """Windows-style path traversal with '..\\' should be rejected."""
    import pytest
    with pytest.raises(ValueError, match="parent directory"):
        TodoStorage("..\\..\\windows\\system32")


def test_storage_accepts_safe_relative_paths() -> None:
    """Safe relative paths without traversal should work normally."""
    storage = TodoStorage("safe.json")
    assert storage.path == Path("safe.json")


def test_storage_accepts_subdirectory_paths() -> None:
    """Paths to subdirectories without traversal should work."""
    storage = TodoStorage("subdir/nested.json")
    assert storage.path == Path("subdir/nested.json")


def test_storage_accepts_absolute_paths() -> None:
    """Absolute paths should be allowed for legitimate use cases."""
    storage = TodoStorage("/tmp/test.json")
    assert storage.path == Path("/tmp/test.json")
