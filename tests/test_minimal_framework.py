"""Tests for the minimal Todo framework."""

from __future__ import annotations

import pytest

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


def test_cli_run_command_flow(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db = "cli.json"
    parser = build_parser()

    args = parser.parse_args(["--db", db, "add", "task"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "task" in out


def test_cli_run_command_returns_error_for_missing_todo(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db = "cli.json"
    parser = build_parser()

    args = parser.parse_args(["--db", db, "done", "99"])
    assert run_command(args) == 1
    out = capsys.readouterr().out
    assert "not found" in out


class TestPathTraversalSecurity:
    """Security tests for path traversal vulnerability via user-controlled db_path."""

    def test_storage_rejects_path_traversal_with_parent_dot_dot(self, tmp_path, monkeypatch) -> None:
        """Path traversal using '../' sequences should be rejected."""
        # Change to tmp_path so we can test path traversal from there
        monkeypatch.chdir(tmp_path)
        storage = TodoStorage("subdir/../../etc/passwd", validate=True)
        with pytest.raises(ValueError, match="outside the current working directory"):
            storage.load()

    def test_storage_rejects_absolute_path_outside_cwd(self) -> None:
        """Absolute paths outside current working directory should be rejected."""
        storage = TodoStorage("/etc/passwd", validate=True)
        with pytest.raises(ValueError, match="outside the current working directory"):
            storage.load()

    def test_storage_rejects_symlink_escape(self, tmp_path, monkeypatch) -> None:
        """Symlinks pointing outside allowed directory should be detected and rejected."""
        # Change to tmp_path so we can test symlink escape from there
        monkeypatch.chdir(tmp_path)
        # Create a symlink inside tmp_path pointing outside
        evil_link = tmp_path / "escape"
        evil_link.symlink_to("/etc")

        storage = TodoStorage("escape/passwd", validate=True)
        with pytest.raises(ValueError, match="outside the current working directory"):
            storage.load()

    def test_storage_allows_safe_relative_path(self, tmp_path, monkeypatch) -> None:
        """Normal relative paths within allowed directory should work."""
        monkeypatch.chdir(tmp_path)
        storage = TodoStorage("safe.json", validate=True)
        todos = [Todo(id=1, text="safe")]
        storage.save(todos)  # Should not raise
        loaded = storage.load()
        assert len(loaded) == 1

    def test_storage_allows_safe_absolute_path_within_cwd(self, tmp_path, monkeypatch) -> None:
        """Absolute paths within current working directory should work."""
        monkeypatch.chdir(tmp_path)
        storage = TodoStorage(str(tmp_path / "safe.json"), validate=True)
        todos = [Todo(id=1, text="safe")]
        storage.save(todos)  # Should not raise
        loaded = storage.load()
        assert len(loaded) == 1
