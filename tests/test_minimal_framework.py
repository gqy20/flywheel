"""Tests for the minimal Todo framework."""

from __future__ import annotations

import json

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
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


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


def test_todo_rename_rejects_empty_string() -> None:
    """Bug #2085: Todo.rename() should reject empty strings after strip."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Empty string should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("")

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_rejects_whitespace_only() -> None:
    """Bug #2085: Todo.rename() should reject whitespace-only strings."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Various whitespace-only strings should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename(" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("\t\n")

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_accepts_valid_text() -> None:
    """Bug #2085: Todo.rename() should still work with valid text."""
    todo = Todo(id=1, text="original")

    # Valid rename should work
    todo.rename("new text")
    assert todo.text == "new text"

    # Whitespace should be stripped
    todo.rename("  padded  ")
    assert todo.text == "padded"


def test_from_dict_accepts_missing_timestamp() -> None:
    """Issue #5326: from_dict should handle missing timestamp fields gracefully.

    When timestamps are not provided, __post_init__ will generate them.
    """
    # Missing timestamp should default to empty string (triggers __post_init__)
    todo = Todo.from_dict({"id": 1, "text": "x"})
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at  # Should be ISO format


def test_from_dict_rejects_non_iso_timestamp() -> None:
    """Issue #5326: from_dict should validate ISO 8601 format for timestamps.

    When a timestamp is provided but is not in ISO 8601 format, it should
    raise a clear error to ensure data consistency.
    """
    # Valid ISO 8601 format should be accepted
    valid_iso = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "x", "created_at": valid_iso})
    assert todo.created_at == valid_iso

    # Valid ISO 8601 with Z suffix
    todo = Todo.from_dict({"id": 1, "text": "x", "created_at": "2024-01-15T10:30:00Z"})
    assert todo.created_at == "2024-01-15T10:30:00Z"

    # Valid ISO 8601 with microseconds
    todo = Todo.from_dict({"id": 1, "text": "x", "created_at": "2024-01-15T10:30:00.123456Z"})
    assert todo.created_at == "2024-01-15T10:30:00.123456Z"

    # Invalid non-ISO format should raise ValueError
    with pytest.raises(ValueError, match="ISO 8601"):
        Todo.from_dict({"id": 1, "text": "x", "created_at": "invalid-date"})

    # Integer should raise ValueError
    with pytest.raises(ValueError, match="ISO 8601"):
        Todo.from_dict({"id": 1, "text": "x", "created_at": 12345})

    # Invalid format for updated_at should also raise
    with pytest.raises(ValueError, match="ISO 8601"):
        Todo.from_dict({"id": 1, "text": "x", "updated_at": "2024/01/15"})
