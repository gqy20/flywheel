"""Tests for the minimal Todo framework."""

from __future__ import annotations

import json
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


def test_storage_load_invalid_json_raises_valueerror(tmp_path) -> None:
    """Invalid JSON files should raise ValueError (not JSONDecodeError)."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create file with invalid JSON content
    db.write_text("{invalid json content", encoding="utf-8")

    # Should raise ValueError (not JSONDecodeError) with helpful message
    try:
        storage.load()
        raise AssertionError("Expected ValueError for invalid JSON file")
    except ValueError as e:
        # Error message should include file path context
        error_msg = str(e).lower()
        assert "json" in error_msg or "parse" in error_msg or "invalid" in error_msg


def test_storage_load_not_json_raises_valueerror(tmp_path) -> None:
    """Non-JSON files should raise ValueError with helpful error."""
    db = tmp_path / "notjson.json"
    storage = TodoStorage(str(db))

    # Create file with plain text content
    db.write_text("this is not json at all", encoding="utf-8")

    # Should raise ValueError
    try:
        storage.load()
        raise AssertionError("Expected ValueError for non-JSON file")
    except ValueError as e:
        error_msg = str(e).lower()
        assert "json" in error_msg or "parse" in error_msg or "invalid" in error_msg


def test_cli_handles_invalid_json_gracefully(tmp_path, capsys) -> None:
    """CLI should handle invalid JSON files with friendly error message."""
    db = str(tmp_path / "invalid.json")
    parser = build_parser()

    # Create invalid JSON file
    Path(db).write_text("{broken", encoding="utf-8")

    # Try to list todos - should exit with error code 1
    args = parser.parse_args(["--db", db, "list"])
    exit_code = run_command(args)

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "Error:" in out
