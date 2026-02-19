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


# Issue #4537: __eq__ and __hash__ tests


def test_todo_eq_same_id_and_text_returns_true() -> None:
    """Issue #4537: Todos with same id and text should be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Issue #4537: Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_eq_different_text_returns_false() -> None:
    """Issue #4537: Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 != todo2


def test_todo_eq_non_todo_returns_not_implemented() -> None:
    """Issue #4537: Comparing Todo with non-Todo should return False."""
    todo = Todo(id=1, text="a")
    assert todo != "not a todo"
    assert todo != 1
    assert todo != None


def test_todo_hash_consistent_for_same_id() -> None:
    """Issue #4537: Todos with same id should have same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_id() -> None:
    """Issue #4537: Todos with different id should have different hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    # Different ids should typically have different hashes (not guaranteed but expected)
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Issue #4537: Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Issue #4537: Set should deduplicate Todos by id (since hash is based on id)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")  # Same id, same text
    todo_set = {todo1, todo2}
    # Since hash is based on id only, and eq compares id AND text,
    # these are different objects with same hash but not equal
    # In a set, they will be treated as duplicates only if hash AND eq match
    assert todo1 == todo2  # Equal (same id and text)
    assert hash(todo1) == hash(todo2)  # Same hash
    assert len(todo_set) == 1  # Deduplicated


def test_todo_in_list_assertion() -> None:
    """Issue #4537: Support 'todo in todos' style assertions in tests."""
    todo = Todo(id=1, text="demo")
    todos = [Todo(id=1, text="demo"), Todo(id=2, text="other")]
    assert todo in todos
