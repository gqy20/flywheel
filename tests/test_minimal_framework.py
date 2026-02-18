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


# ============================================================================
# Due Date Feature Tests (Issue #4106)
# ============================================================================


def test_todo_with_due_date_creates_correctly() -> None:
    """Issue #4106: Todo should support optional due_at field."""
    todo = Todo(id=1, text="task with deadline", due_at="2024-12-31T23:59:59+00:00")

    assert todo.due_at == "2024-12-31T23:59:59+00:00"


def test_todo_is_overdue_returns_true_for_past_dates() -> None:
    """Issue #4106: is_overdue should return True for past due dates."""
    todo = Todo(
        id=1, text="overdue task", due_at="2020-01-01T00:00:00+00:00"
    )

    assert todo.is_overdue is True


def test_todo_is_overdue_returns_false_for_future_dates() -> None:
    """Issue #4106: is_overdue should return False for future due dates."""
    todo = Todo(
        id=1, text="future task", due_at="2099-12-31T23:59:59+00:00"
    )

    assert todo.is_overdue is False


def test_todo_is_overdue_returns_false_when_due_at_is_none() -> None:
    """Issue #4106: is_overdue should return False when due_at is None."""
    todo = Todo(id=1, text="no deadline")

    assert todo.due_at is None
    assert todo.is_overdue is False


def test_todo_to_dict_includes_due_at() -> None:
    """Issue #4106: to_dict should include due_at field."""
    todo = Todo(id=1, text="task", due_at="2024-06-15T12:00:00+00:00")

    result = todo.to_dict()

    assert "due_at" in result
    assert result["due_at"] == "2024-06-15T12:00:00+00:00"


def test_todo_from_dict_handles_due_at() -> None:
    """Issue #4106: from_dict should correctly load due_at field."""
    data = {"id": 1, "text": "task", "due_at": "2024-06-15T12:00:00+00:00"}

    todo = Todo.from_dict(data)

    assert todo.due_at == "2024-06-15T12:00:00+00:00"


def test_todo_backward_compatible_without_due_at() -> None:
    """Issue #4106: Loading todos without due_at should work (backward compat)."""
    data = {"id": 1, "text": "legacy task", "done": False}

    todo = Todo.from_dict(data)

    assert todo.due_at is None
    assert todo.is_overdue is False
