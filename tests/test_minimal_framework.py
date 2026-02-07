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


def test_storage_load_rejects_oversized_json(tmp_path) -> None:
    """Security: JSON files larger than 10MB should be rejected to prevent DoS."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB (~11MB of data)
    # Using a simple repeated pattern to ensure sufficient size
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > 10 * 1024 * 1024

    # Should raise ValueError for oversized file
    try:
        storage.load()
        raise AssertionError("Expected ValueError for oversized JSON file")
    except ValueError as e:
        assert "too large" in str(e).lower() or "size" in str(e).lower()


def test_storage_load_accepts_normal_sized_json(tmp_path) -> None:
    """Verify normal-sized JSON files are still accepted."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a normal small JSON file
    todos = [Todo(id=1, text="normal todo")]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"


def test_main_fails_when_db_parent_is_existing_file(tmp_path, capsys) -> None:
    """Security: When db parent path is an existing file (not directory), should fail gracefully."""
    # Create a file where we expect a directory
    existing_file = tmp_path / "db.json"
    existing_file.write_text("I am a file, not a directory")

    # Try to use a path that requires the file to be a directory
    db_path = str(existing_file / "subdir" / "todo.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should fail with appropriate error (not FileExistsError unhandled)
    result = run_command(args)
    assert result == 1

    out = capsys.readouterr().out
    # Should have a meaningful error message, not a traceback
    assert "Error:" in out


def test_main_fails_on_permission_denied_for_directory_creation(tmp_path, capsys) -> None:
    """Security: When directory creation fails due to permissions, should surface error properly."""
    # Create a directory with no write permissions
    no_write_dir = tmp_path / "no_write"
    no_write_dir.mkdir()

    try:
        # Remove write permissions
        no_write_dir.chmod(0o000)

        # Try to create a subdirectory (should fail permission denied)
        db_path = str(no_write_dir / "subdir" / "todo.json")

        parser = build_parser()
        args = parser.parse_args(["--db", db_path, "add", "test"])

        # Should fail gracefully, not crash
        result = run_command(args)
        assert result == 1

        out = capsys.readouterr().out
        assert "Error:" in out
    finally:
        # Restore permissions for cleanup
        no_write_dir.chmod(0o755)
