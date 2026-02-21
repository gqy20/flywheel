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


def test_next_id_with_only_zero_ids() -> None:
    """Bug #4560: next_id should return unique ID when all IDs are 0.

    The problem: when all existing IDs are 0, next_id returns 1.
    This is the same value returned for an empty list.
    While 1 is technically correct (max of [0] is 0, 0+1=1),
    the issue is about ensuring IDs are always unique.

    The acceptance criteria states: "next_id never returns 0 since Todo.id is typically >= 1"
    So when all IDs are 0, we should return a positive ID (>= 1) that doesn't collide.
    """
    storage = TodoStorage("/tmp/test.json")

    # Edge case: todos with ALL IDs being 0 (invalid/malformed data)
    todos = [Todo(id=0, text="zero id todo")]

    next_id = storage.next_id(todos)

    # next_id should return a positive ID (>= 1), not 0
    assert next_id >= 1

    # The returned ID should ideally not collide with existing IDs
    # Since all existing IDs are 0, and next_id returns 1, this is fine
    # But the key insight is: we should ensure it's >= 1
    existing_ids = {todo.id for todo in todos}
    # If next_id is 1, it won't be in existing_ids (which only contains 0)
    assert next_id not in existing_ids


def test_next_id_empty_list_vs_all_zeros_distinguishable() -> None:
    """Bug #4560: Ensure next_id handles empty list and all-zeros list correctly.

    Both cases return 1, which is acceptable as long as:
    1. Empty list returns 1 (correct)
    2. List with all zeros returns a value >= 1 that doesn't collide with existing

    This test verifies the acceptance criteria: "next_id never returns 0"
    """
    storage = TodoStorage("/tmp/test.json")

    # Empty list should return 1
    empty_next_id = storage.next_id([])
    assert empty_next_id == 1

    # List with all zeros should also return a positive ID (>= 1)
    zero_todos = [Todo(id=0, text="zero")]
    zero_next_id = storage.next_id(zero_todos)
    assert zero_next_id >= 1

    # Key requirement: next_id should never return 0
    assert empty_next_id != 0
    assert zero_next_id != 0


def test_next_id_never_returns_existing_id() -> None:
    """Bug #4560: next_id should never return an ID that already exists.

    The core issue: if we have todos with mixed valid and zero IDs,
    next_id must ensure it doesn't return an existing ID.

    Example scenario that could cause collision:
    - todos = [Todo(id=0), Todo(id=1)]
    - max() returns 1, so next_id returns 2 (correct!)

    This test ensures the acceptance criteria:
    "next_id returns unique ID regardless of existing ID values"
    """
    storage = TodoStorage("/tmp/test.json")

    # Test various edge cases where collision could occur
    test_cases = [
        # (todos, expected_not_in_set)
        ([Todo(id=0, text="t0"), Todo(id=1, text="t1")], {0, 1}),
        ([Todo(id=0, text="t0"), Todo(id=2, text="t2")], {0, 2}),
        ([Todo(id=0, text="t0"), Todo(id=1, text="t1"), Todo(id=2, text="t2")], {0, 1, 2}),
    ]

    for todos, existing_ids in test_cases:
        next_id = storage.next_id(todos)
        # Verify the returned ID doesn't collide with any existing ID
        assert next_id not in existing_ids, (
            f"next_id={next_id} collides with existing IDs {existing_ids}"
        )
