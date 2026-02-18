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


# === Feature #4134: due_date field for task scheduling ===


def test_todo_has_due_date_field() -> None:
    """Feature #4134: Todo dataclass should include due_date field."""
    todo = Todo(id=1, text="task with due date", due_date="2026-03-01")
    assert todo.due_date == "2026-03-01"

    # Default should be empty string
    todo_no_due = Todo(id=2, text="task without due date")
    assert todo_no_due.due_date == ""


def test_todo_is_overdue_with_past_date() -> None:
    """Feature #4134: is_overdue() should return True for past dates."""
    todo = Todo(id=1, text="overdue task", due_date="2020-01-01")
    assert todo.is_overdue() is True


def test_todo_is_overdue_with_future_date() -> None:
    """Feature #4134: is_overdue() should return False for future dates."""
    todo = Todo(id=1, text="future task", due_date="2030-12-31")
    assert todo.is_overdue() is False


def test_todo_is_overdue_with_no_due_date() -> None:
    """Feature #4134: is_overdue() should return False when no due date set."""
    todo = Todo(id=1, text="no due date task", due_date="")
    assert todo.is_overdue() is False


def test_todo_is_overdue_completed_task() -> None:
    """Feature #4134: Completed tasks should not be considered overdue."""
    todo = Todo(id=1, text="completed overdue task", due_date="2020-01-01", done=True)
    assert todo.is_overdue() is False


def test_todo_from_dict_with_due_date() -> None:
    """Feature #4134: from_dict should handle due_date field."""
    data = {"id": 1, "text": "task", "due_date": "2026-03-01"}
    todo = Todo.from_dict(data)
    assert todo.due_date == "2026-03-01"


def test_todo_to_dict_includes_due_date() -> None:
    """Feature #4134: to_dict should include due_date field."""
    todo = Todo(id=1, text="task", due_date="2026-03-01")
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] == "2026-03-01"


def test_storage_roundtrip_with_due_date(tmp_path) -> None:
    """Feature #4134: Storage should persist and restore due_date."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task with due", due_date="2026-03-01")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].due_date == "2026-03-01"


def test_cli_add_with_due_flag(tmp_path, capsys) -> None:
    """Feature #4134: CLI add command should support --due flag."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "add", "task", "--due", "2026-03-01"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    assert "task" in out

    # Verify the todo was saved with due_date
    app = TodoApp(db)
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].due_date == "2026-03-01"


def test_cli_list_shows_overdue_status(tmp_path, capsys) -> None:
    """Feature #4134: List command should visually show overdue status."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add an overdue task
    app.add("overdue task", due_date="2020-01-01")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    # Overdue tasks should show some indicator
    assert "overdue" in out.lower() or "!" in out
