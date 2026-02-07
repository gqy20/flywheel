"""Tests for the minimal Todo framework."""

from __future__ import annotations

import shutil
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


def test_storage_roundtrip() -> None:
    # Use a subdirectory within cwd for testing
    test_dir = Path.cwd() / "test_storage_roundtrip"
    test_dir.mkdir(exist_ok=True)

    try:
        db = test_dir / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="x"), Todo(id=2, text="y", done=True)]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "x"
        assert loaded[1].done is True
        assert storage.next_id(loaded) == 3
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_app_add_done_remove() -> None:
    # Use a subdirectory within cwd for testing
    test_dir = Path.cwd() / "test_app_add_done_remove"
    test_dir.mkdir(exist_ok=True)

    try:
        app = TodoApp(str(test_dir / "db.json"))

        added = app.add("demo")
        assert added.id == 1
        assert app.list()[0].text == "demo"

        app.mark_done(1)
        assert app.list()[0].done is True

        app.remove(1)
        assert app.list() == []
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_run_command_flow(capsys) -> None:
    # Use a subdirectory within cwd for testing
    test_dir = Path.cwd() / "test_cli_run_command_flow"
    test_dir.mkdir(exist_ok=True)

    try:
        db = str(test_dir / "cli.json")
        parser = build_parser()

        args = parser.parse_args(["--db", db, "add", "task"])
        assert run_command(args) == 0

        args = parser.parse_args(["--db", db, "list"])
        assert run_command(args) == 0
        out = capsys.readouterr().out
        assert "task" in out
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_cli_run_command_returns_error_for_missing_todo(capsys) -> None:
    # Use a subdirectory within cwd for testing
    test_dir = Path.cwd() / "test_cli_run_command_error"
    test_dir.mkdir(exist_ok=True)

    try:
        db = str(test_dir / "cli.json")
        parser = build_parser()

        args = parser.parse_args(["--db", db, "done", "99"])
        assert run_command(args) == 1
        out = capsys.readouterr().out
        assert "not found" in out
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
