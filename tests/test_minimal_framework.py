"""Tests for the minimal Todo framework."""

from __future__ import annotations

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


def test_storage_rejects_path_traversal_attacks(tmp_path) -> None:
    """Test that TodoStorage rejects paths containing '..' to prevent directory traversal."""
    import pytest

    # Test various path traversal attempts
    traversal_paths = [
        "../../../tmp/evil.json",
        "../../sensitive.json",
        "../etc/passwd",
        "./../../escape.json",
        "normal/../../../escape.json",
    ]

    for malicious_path in traversal_paths:
        with pytest.raises(ValueError, match=r"\.\..*directory traversal"):
            TodoStorage(malicious_path)

    # Test that paths with absolute paths but containing '..' are also rejected
    with pytest.raises(ValueError, match=r"\.\..*directory traversal"):
        TodoStorage("/tmp/../etc/passwd")


def test_storage_allows_safe_paths_within_cwd(tmp_path) -> None:
    """Test that TodoStorage allows safe relative paths within current directory."""
    import os

    # Save original CWD
    original_cwd = os.getcwd()

    try:
        # Change to tmp_path for testing
        os.chdir(tmp_path)

        # These should all be allowed
        safe_paths = [
            "todo.json",
            "./todo.json",
            "subdir/todo.json",
            "./subdir/todo.json",
        ]

        for safe_path in safe_paths:
            storage = TodoStorage(safe_path)
            assert storage.path is not None

        # Test that actual save/load works for safe paths
        storage = TodoStorage("safe.json")
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    finally:
        # Restore original CWD
        os.chdir(original_cwd)
