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


def test_todo_post_init_preserves_falsy_string_values() -> None:
    """Bug #2869: __post_init__ should preserve string '0', 'False' instead of overwriting them.

    The issue is that `if not self.created_at:` uses falsy check which treats
    integer 0 and boolean False as empty, causing them to be overwritten with
    timestamps even though they coerce to valid strings '0' and 'False'.
    """
    # Test integer 0 - should be preserved as string '0'
    todo_int_zero = Todo(id=1, text="test", created_at=0, updated_at=0)
    assert todo_int_zero.created_at == "0", "Integer 0 should be preserved as '0'"
    assert todo_int_zero.updated_at == "0", "Integer 0 for updated_at should be preserved as '0'"

    # Test boolean False - should be preserved as string 'False'
    todo_bool_false = Todo(id=1, text="test", created_at=False, updated_at=False)
    assert todo_bool_false.created_at == "False", "Boolean False should be preserved as 'False'"
    assert todo_bool_false.updated_at == "False", "Boolean False for updated_at should be preserved as 'False'"

    # Test empty string - should generate new timestamp (expected behavior)
    todo_empty = Todo(id=1, text="test", created_at="", updated_at="")
    assert todo_empty.created_at != "", "Empty string should generate timestamp"
    assert todo_empty.updated_at == todo_empty.created_at, "Empty updated_at should use created_at"

    # Test that valid ISO timestamps are preserved
    valid_timestamp = "2024-01-01T00:00:00+00:00"
    todo_valid = Todo(id=1, text="test", created_at=valid_timestamp, updated_at=valid_timestamp)
    assert todo_valid.created_at == valid_timestamp, "Valid timestamp should be preserved"
    assert todo_valid.updated_at == valid_timestamp, "Valid timestamp should be preserved"

    # Test string '0' (already a string) - should be preserved
    todo_str_zero = Todo(id=1, text="test", created_at="0", updated_at="0")
    assert todo_str_zero.created_at == "0", "String '0' should be preserved"
    assert todo_str_zero.updated_at == "0", "String '0' should be preserved"

    # Test string 'False' (already a string) - should be preserved
    todo_str_false = Todo(id=1, text="test", created_at="False", updated_at="False")
    assert todo_str_false.created_at == "False", "String 'False' should be preserved"
    assert todo_str_false.updated_at == "False", "String 'False' should be preserved"
