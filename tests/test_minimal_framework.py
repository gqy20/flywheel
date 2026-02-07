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


def test_storage_rejects_files_exceeding_10mb_limit(tmp_path) -> None:
    """Test that files larger than 10MB are rejected to prevent DoS attacks (issue #1868)."""
    import json

    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a 11MB JSON payload (exceeds 10MB limit)
    large_payload = [{"id": i, "text": "x" * 100} for i in range(110000)]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Should raise ValueError for files exceeding 10MB
    import pytest
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        storage.load()


def test_storage_accepts_files_within_10mb_limit(tmp_path) -> None:
    """Test that files within 10MB limit are accepted (issue #1868)."""
    import json

    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a small 1KB JSON payload (well within 10MB limit)
    small_payload = [{"id": 1, "text": "normal todo"}]
    db.write_text(json.dumps(small_payload), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"
