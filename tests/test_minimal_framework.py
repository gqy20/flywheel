"""Tests for the minimal Todo framework."""

from __future__ import annotations

from pathlib import Path

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


# Security tests for path traversal vulnerability (Issue #1883)
def test_storage_rejects_path_traversal_with_parent_refs() -> None:
    """Should reject paths with ../ sequences to prevent directory traversal."""
    with pytest.raises(ValueError, match="outside the current working directory"):
        TodoStorage("../../../etc/passwd", validate=True)


def test_storage_rejects_absolute_paths_outside_cwd() -> None:
    """Should reject absolute paths outside current working directory."""
    with pytest.raises(ValueError, match="outside the current working directory"):
        TodoStorage("/tmp/evil.json", validate=True)


def test_storage_rejects_absolute_path_etc_shadow() -> None:
    """Should reject attempts to access sensitive system files."""
    with pytest.raises(ValueError, match="outside the current working directory"):
        TodoStorage("/etc/shadow", validate=True)


def test_storage_rejects_complex_path_traversal() -> None:
    """Should reject complex path traversal attempts."""
    with pytest.raises(ValueError, match="outside the current working directory"):
        TodoStorage("./../../tmp/test.json", validate=True)


def test_storage_allows_safe_paths_with_validation() -> None:
    """Should allow paths within current working directory when validation is enabled."""
    # Create a test file in current directory
    test_path = Path.cwd() / "test_safe.json"
    storage = TodoStorage("test_safe.json", validate=True)
    assert storage.path == test_path.resolve()


def test_storage_allows_simple_filename() -> None:
    """Should allow simple filename in current directory."""
    storage = TodoStorage("todo.json")
    # Without validation, path is not resolved
    assert storage.path == Path("todo.json")

    # With validation, path is resolved
    storage_validated = TodoStorage("todo.json", validate=True)
    assert storage_validated.path == (Path.cwd() / "todo.json").resolve()


def test_storage_rejects_symlink_outside_allowed_directory(tmp_path) -> None:
    """Should reject symlinks that point outside allowed directory."""
    # Create a symlink in CWD pointing outside
    cwd = Path.cwd()
    outside_link = cwd / "escape_link"
    target = tmp_path.parent / "target_file.json"
    target.write_text("{}")

    try:
        outside_link.symlink_to(target)
    except (OSError, NotImplementedError):
        # Skip test if symlinks not supported
        pytest.skip("Symlinks not supported on this system")
        return

    try:
        # This should be rejected
        with pytest.raises(ValueError, match="outside the current working directory"):
            TodoStorage(str(outside_link), validate=True)
    finally:
        # Clean up symlink
        outside_link.unlink(missing_ok=True)
