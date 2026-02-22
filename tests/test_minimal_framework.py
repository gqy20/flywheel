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


def test_next_id_returns_valid_id_for_non_contiguous_ids(tmp_path) -> None:
    """Bug #5188: next_id should return a valid ID not in existing set.

    When IDs are non-contiguous (e.g., [1, 5]), the next_id should return
    an ID that doesn't conflict with any existing ID.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Non-contiguous IDs: 1, 5 (gap at 2, 3, 4)
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b")]
    storage.save(todos)

    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # next_id should not conflict with any existing ID
    assert next_id not in {todo.id for todo in loaded}


def test_next_id_returns_valid_id_for_negative_ids(tmp_path) -> None:
    """Bug #5188: next_id should return a valid positive ID even with negative IDs.

    When IDs include negative values, next_id should still return a valid
    positive integer that doesn't conflict with existing IDs.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Include negative IDs: -5, -1, 3
    todos = [
        Todo(id=-5, text="negative1"),
        Todo(id=-1, text="negative2"),
        Todo(id=3, text="positive"),
    ]
    storage.save(todos)

    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # next_id should be a valid positive integer
    assert next_id > 0
    # The issue: if max is 3, next_id = 4, which is valid
    # But if max was negative, next_id could be 0 or negative
    # With the fix, we ensure it's always positive and unique
    assert next_id not in {todo.id for todo in loaded}


def test_next_id_returns_valid_id_after_max_deletion(tmp_path) -> None:
    """Bug #5188: next_id should not duplicate IDs after max ID is deleted.

    Scenario:
    1. Start with [1, 5, 10]
    2. Delete ID 10 -> remaining: [1, 5]
    3. next_id should return 6, not 6 (which is fine)
    4. Add new todo with ID 6 -> [1, 5, 6]
    5. next_id should return 7, not 6 again
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start with [1, 5, 10]
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
    storage.save(todos)

    # Delete ID 10
    todos = [t for t in todos if t.id != 10]
    storage.save(todos)

    # next_id should be 6
    next_id = storage.next_id(todos)
    assert next_id == 6

    # Add new todo with ID 6
    todos.append(Todo(id=next_id, text="new"))
    storage.save(todos)

    # next_id should now be 7, not 6 (duplicate)
    next_id_2 = storage.next_id(todos)
    assert next_id_2 == 7
    assert next_id_2 not in {todo.id for todo in todos}


def test_next_id_returns_1_for_empty_list(tmp_path) -> None:
    """Bug #5188: next_id should return 1 for an empty todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty list should return 1
    next_id = storage.next_id([])
    assert next_id == 1


def test_next_id_returns_valid_positive_id_when_all_ids_are_negative(tmp_path) -> None:
    """Bug #5188: next_id should return positive ID even when all IDs are negative.

    This is the core bug: if all existing IDs are negative (e.g., [-5, -1]),
    max() returns -1, and next_id would return 0 (which is not a valid positive ID).

    The fix ensures next_id always returns a valid positive integer >= 1.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # All IDs are negative
    todos = [Todo(id=-5, text="negative1"), Todo(id=-1, text="negative2")]
    storage.save(todos)

    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # next_id should be a valid positive integer (>= 1)
    assert next_id >= 1, f"Expected positive ID, got {next_id}"
    # Should not conflict with any existing ID
    assert next_id not in {todo.id for todo in loaded}


def test_next_id_returns_valid_positive_id_when_max_is_zero(tmp_path) -> None:
    """Bug #5188: next_id should return positive ID even when max ID is 0.

    If IDs include 0 as the max, next_id would return 1, which is fine.
    But if IDs are [-2, 0], max() returns 0, and next_id returns 1.
    This test ensures that case works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # IDs include 0 as max
    todos = [Todo(id=-2, text="negative"), Todo(id=0, text="zero")]
    storage.save(todos)

    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # next_id should be >= 1
    assert next_id >= 1, f"Expected positive ID >= 1, got {next_id}"
    # Should not conflict with any existing ID
    assert next_id not in {todo.id for todo in loaded}
