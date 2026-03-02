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


def test_next_id_performance_with_large_todo_list(tmp_path) -> None:
    """Issue #6855: next_id() should be O(1) not O(n) for large todo lists.

    This test verifies that next_id() performance does not degrade
    significantly with large todo lists (>1000 items).
    """
    import time

    db = tmp_path / "perf.json"
    storage = TodoStorage(str(db))

    # Create 10,000 todos to simulate large list
    large_todo_list = [Todo(id=i, text=f"task {i}") for i in range(1, 10001)]
    storage.save(large_todo_list)

    # Load to populate cache
    loaded = storage.load()

    # Measure next_id performance - should be O(1) with caching
    # With O(n) implementation, this would take ~10ms+ for 10,000 items
    # With O(1) caching, should be <1ms
    start = time.perf_counter()
    result = storage.next_id(loaded)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result == 10001
    # Assert O(1) performance: should be <5ms even for 10,000 items
    # (allowing some margin for test environment variability)
    assert elapsed_ms < 5.0, f"next_id took {elapsed_ms:.2f}ms, expected <5ms for O(1)"


def test_next_id_correctness_after_load(tmp_path) -> None:
    """Issue #6855: Verify next_id returns correct values after loading existing todos."""
    db = tmp_path / "correctness.json"
    storage = TodoStorage(str(db))

    # Create todos with non-sequential IDs to test edge cases
    todos = [
        Todo(id=5, text="task 5"),
        Todo(id=10, text="task 10"),
        Todo(id=3, text="task 3"),
    ]
    storage.save(todos)

    # Load and verify next_id returns max+1
    loaded = storage.load()
    assert storage.next_id(loaded) == 11


def test_next_id_sequential_adds(tmp_path) -> None:
    """Issue #6855: Verify sequential ID assignment works correctly with caching."""
    db = tmp_path / "sequential.json"
    storage = TodoStorage(str(db))

    # Add multiple todos and verify sequential IDs
    todos = []
    for i in range(1, 101):
        todo = Todo(id=storage.next_id(todos), text=f"task {i}")
        todos.append(todo)

    # Verify IDs are sequential starting from 1
    assert [t.id for t in todos] == list(range(1, 101))
